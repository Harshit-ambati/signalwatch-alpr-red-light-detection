import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import cv2
from .rules import CrossingDetector
from .vision import signal_state, PlateReader, select_plate_read


def box_iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2-x1) * max(0, y2-y1)
    area_a = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    area_b = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def process(video, config, progress=None):
    from ultralytics import YOLO
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not cap.isOpened() or fps <= 0:
        cap.release()
        raise ValueError('Cannot decode video or determine frame rate.')
    start_frame = max(0, int(config.get('start_seconds', 0) * fps))
    if total > 0 and start_frame >= total:
        cap.release()
        raise ValueError('Start time is beyond the end of the video.')
    if start_frame:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    run = Path('data/runs') / uuid4().hex[:12]
    run.mkdir(parents=True)
    manifest = {'id':run.name, 'created':datetime.now(timezone.utc).isoformat(), 'source':Path(video).name,
                'config':config, 'status':'processing', 'events':[], 'plate_scans':[]}
    def save():
        target = run/'results.json'
        tmp = run/'results.tmp'
        tmp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        tmp.replace(target)
    save()
    try:
        detector = YOLO('yolo11n.pt')
        reader = PlateReader(config.get('plate_model')) if config['ocr'] else None
        rules = CrossingDetector(config['line'][0], config['line'][1], config['direction'],
                                 approach_zone=config.get('approach_zone'))
        previous_frames = {}
        recent_crops = {}
        recent_reads = {}
        scan_attempts = {}
        last_scan_time = {}
        scan_index = {}
        recent_reports = []
        raw_state, stable_count = 'unknown', 0
        signal_counts = {'red': 0, 'green': 0, 'amber': 0, 'unknown': 0}
        index = start_frame
        processed = 0
        while True:
            if config.get('max_seconds', 0) and processed/fps >= config['max_seconds']:
                break
            ok, frame = cap.read()
            if not ok:
                break
            t = index/fps
            h,w = frame.shape[:2]
            if config['signal_mode'] == 'Plate scan only':
                state = 'unknown'
            elif config['signal_mode'] == 'Manual timeline':
                state = 'red' if any(a <= t < b for a,b in config['red_intervals']) else 'unknown'
            else:
                observed = signal_state(frame, config['roi'])
                stable_count = stable_count+1 if observed == raw_state else 1
                raw_state = observed
                state = observed if stable_count >= 3 else 'unknown'
            signal_counts[state] += 1
            result = detector.track(frame, persist=True, tracker='bytetrack.yaml', classes=[2,3,5,7], conf=0.3, verbose=False)[0]
            annotated = frame.copy()
            a,b = [tuple((int(p[0]*w), int(p[1]*h))) for p in config['line']]
            cv2.line(annotated,a,b,(0,200,255),3)
            if config.get('approach_zone'):
                lx1, ly1, lx2, ly2 = config['approach_zone']
                cv2.rectangle(annotated,(int(lx1*w),int(ly1*h)),(int(lx2*w),int(ly2*h)),(50,220,50),2)
            cv2.putText(annotated, f'{state.upper()} | {t:.2f}s', (20,35), 0, 0.8,(255,255,255),2)
            active = set()
            if result.boxes.id is not None:
                for box,track in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.id.int().cpu().tolist()):
                    active.add(track)
                    x1,y1,x2,y2 = map(int,box)
                    x1,y1,x2,y2 = max(0,x1),max(0,y1),min(w,x2),min(h,y2)
                    crop = frame[y1:y2,x1:x2]
                    if not crop.size:
                        continue
                    # Bottom center is an approximate road-contact anchor, not a wheel measurement.
                    point = ((x1+x2)/(2*w),y2/h)
                    crossed = rules.update(track,point,t,state)
                    cv2.rectangle(annotated,(x1,y1),(x2,y2),(40,210,90),2)
                    cv2.putText(annotated,f'ID {track}',(x1,max(15,y1-5)),0,0.5,(40,210,90),1)
                    # Plate scanning is independent of violation screening. Sample large
                    # vehicle crops sparingly so the OCR cost remains bounded.
                    if (reader and x2-x1 >= 120 and y2-y1 >= 75
                            and scan_attempts.get(track, 0) < 5
                            and t-last_scan_time.get(track, float('-inf')) >= 1.0):
                        scan_attempts[track] = scan_attempts.get(track, 0) + 1
                        last_scan_time[track] = t
                        read = reader.read(crop)
                        if read:
                            recent_reads.setdefault(track, []).append(read)
                            recent_reads[track] = recent_reads[track][-5:]
                            best_scan = select_plate_read(recent_reads[track])
                            if track not in scan_index:
                                scan_index[track] = len(manifest['plate_scans'])
                                manifest['plate_scans'].append({'id':f'{scan_index[track]+1:04d}',
                                                                'track_id':track, 'video_seconds':round(t,3),
                                                                'plate':best_scan[0], 'ocr_confidence':round(best_scan[1],3)})
                            else:
                                manifest['plate_scans'][scan_index[track]].update(
                                    plate=best_scan[0], ocr_confidence=round(best_scan[1],3))
                            scan_folder = run/'scans'
                            scan_folder.mkdir(exist_ok=True)
                            cv2.imwrite(str(scan_folder/f'{manifest["plate_scans"][scan_index[track]]["id"]}.jpg'),best_scan[2])
                    if crossed:
                        recent_reports = [(when, reported_box) for when, reported_box in recent_reports if t-when <= 0.5]
                        if any(box_iou(box, reported_box) >= 0.7 for _, reported_box in recent_reports):
                            previous_frames[track] = frame
                            continue
                        recent_reports.append((t, box))
                        event_id = f'{len(manifest["events"])+1:04d}'
                        folder = run/event_id
                        folder.mkdir()
                        cv2.imwrite(str(folder/'crossing.jpg'),annotated)
                        cv2.imwrite(str(folder/'vehicle.jpg'),crop)
                        if track in previous_frames:
                            cv2.imwrite(str(folder/'before.jpg'),previous_frames[track])
                        reads = list(recent_reads.get(track, []))
                        if reader:
                            for candidate in recent_crops.get(track,[]) + [crop]:
                                read = reader.read(candidate)
                                if read:
                                    reads.append(read)
                        best = select_plate_read(reads)
                        if best:
                            cv2.imwrite(str(folder/'plate.jpg'),best[2])
                        manifest['events'].append({'id':event_id,'track_id':track,'video_seconds':round(t,3),
                            'plate':best[0] if best else '', 'ocr_confidence':round(best[1],3) if best else None,
                            'review':'pending','corrected_plate':'','signal_source':config['signal_mode']})
                        save()
                    if index % max(1,int(fps/4)) == 0:
                        recent_crops.setdefault(track,[]).append(crop.copy())
                        recent_crops[track] = recent_crops[track][-4:]
                    previous_frames[track] = frame
            # Drop disconnected tracks to bound image memory; tracker handles short occlusions.
            for track in list(previous_frames):
                if track not in active:
                    previous_frames.pop(track,None)
                    recent_crops.pop(track,None)
            index += 1
            processed += 1
            if progress and processed % 10 == 0:
                remaining = max(0, total-start_frame)
                expected = min(remaining, int(config['max_seconds']*fps)) if config.get('max_seconds') else remaining
                progress(min(processed/max(expected,1),1),annotated,len(manifest['events']))
        if processed == 0:
            raise ValueError('No decodable frames found.')
        manifest['status'] = 'complete'
        manifest['processed_frames'] = processed
        manifest['diagnostics'] = {'signal_frames': signal_counts,
                                   'line_crossings': rules.geometry_crossings,
                                   'plate_scan_attempts':sum(scan_attempts.values())}
    except Exception as exc:
        manifest['status'] = 'failed'
        manifest['error'] = str(exc)
        raise
    finally:
        cap.release()
        save()
    return run
