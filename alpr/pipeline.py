import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import cv2
from .rules import CrossingDetector
from .vision import signal_state, PlateReader


def process(video, config, progress=None):
    from ultralytics import YOLO
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not cap.isOpened() or fps <= 0:
        cap.release()
        raise ValueError('Cannot decode video or determine frame rate.')
    run = Path('data/runs') / uuid4().hex[:12]
    run.mkdir(parents=True)
    manifest = {'id':run.name, 'created':datetime.now(timezone.utc).isoformat(), 'source':Path(video).name,
                'config':config, 'status':'processing', 'events':[]}
    def save():
        target = run/'results.json'
        tmp = run/'results.tmp'
        tmp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        tmp.replace(target)
    save()
    try:
        detector = YOLO('yolo11n.pt')
        reader = PlateReader(config.get('plate_model')) if config['ocr'] else None
        rules = CrossingDetector(config['line'][0], config['line'][1], config['direction'])
        previous_frames = {}
        recent_crops = {}
        raw_state, stable_count = 'unknown', 0
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = index/fps
            if config.get('max_seconds', 0) and t >= config['max_seconds']:
                break
            h,w = frame.shape[:2]
            if config['signal_mode'] == 'Manual timeline':
                state = 'red' if any(a <= t < b for a,b in config['red_intervals']) else 'unknown'
            else:
                observed = signal_state(frame, config['roi'])
                stable_count = stable_count+1 if observed == raw_state else 1
                raw_state = observed
                state = observed if stable_count >= 3 else 'unknown'
            result = detector.track(frame, persist=True, tracker='bytetrack.yaml', classes=[2,3,5,7], conf=0.3, verbose=False)[0]
            annotated = frame.copy()
            a,b = [tuple((int(p[0]*w), int(p[1]*h))) for p in config['line']]
            cv2.line(annotated,a,b,(0,200,255),3)
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
                    if crop.size and index % max(1,int(fps/4)) == 0:
                        recent_crops.setdefault(track,[]).append(crop.copy())
                        recent_crops[track] = recent_crops[track][-4:]
                    if crossed:
                        event_id = f'{len(manifest["events"])+1:04d}'
                        folder = run/event_id
                        folder.mkdir()
                        cv2.imwrite(str(folder/'crossing.jpg'),annotated)
                        cv2.imwrite(str(folder/'vehicle.jpg'),crop)
                        if track in previous_frames:
                            cv2.imwrite(str(folder/'before.jpg'),previous_frames[track])
                        best = None
                        if reader:
                            for candidate in recent_crops.get(track,[]) + [crop]:
                                read = reader.read(candidate)
                                if read and (best is None or read[1] > best[1]):
                                    best = read
                        if best:
                            cv2.imwrite(str(folder/'plate.jpg'),best[2])
                        manifest['events'].append({'id':event_id,'track_id':track,'video_seconds':round(t,3),
                            'plate':best[0] if best else '', 'ocr_confidence':round(best[1],3) if best else None,
                            'review':'pending','corrected_plate':'','signal_source':config['signal_mode']})
                        save()
                    previous_frames[track] = frame
            # Drop disconnected tracks to bound image memory; tracker handles short occlusions.
            for track in list(previous_frames):
                if track not in active:
                    previous_frames.pop(track,None)
                    recent_crops.pop(track,None)
            index += 1
            if progress and index % 10 == 0:
                expected = min(total, int(config['max_seconds']*fps)) if config.get('max_seconds') else total
                progress(min(index/max(expected,1),1),annotated,len(manifest['events']))
        if index == 0:
            raise ValueError('No decodable frames found.')
        manifest['status'] = 'complete'
        manifest['processed_frames'] = index
    except Exception as exc:
        manifest['status'] = 'failed'
        manifest['error'] = str(exc)
        raise
    finally:
        cap.release()
        save()
    return run
