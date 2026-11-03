"""Match predicted crossings to manually labelled events by video timestamp."""
import csv
import io
import re


def normalize_plate(value):
    return re.sub(r'[^A-Z0-9]', '', (value or '').upper())


def read_ground_truth(csv_text):
    reader=csv.DictReader(io.StringIO(csv_text))
    if not {'video_seconds','plate'}.issubset(reader.fieldnames or []):
        raise ValueError('CSV needs video_seconds and plate columns.')
    rows=[]
    for row in reader:
        try:
            stamp=float(row['video_seconds'])
        except (TypeError, ValueError) as exc:
            raise ValueError('Every video_seconds value must be numeric.') from exc
        if stamp < 0:
            raise ValueError('Video timestamps cannot be negative.')
        rows.append({'video_seconds':stamp,'plate':normalize_plate(row['plate'])})
    return rows


def evaluate(events, truth, tolerance=0.5):
    pairs=sorted((abs(float(event['video_seconds'])-row['video_seconds']),i,j)
                 for i,event in enumerate(events) for j,row in enumerate(truth)
                 if abs(float(event['video_seconds'])-row['video_seconds'])<=tolerance)
    matched_events=set(); matched_truth=set(); readable=0; correct=0
    for _,i,j in pairs:
        if i in matched_events or j in matched_truth:
            continue
        matched_events.add(i);matched_truth.add(j)
        if truth[j]['plate']:
            readable+=1
            # Score the model output, not the human correction made during review.
            predicted=events[i].get('plate') or ''
            correct+=normalize_plate(predicted)==truth[j]['plate']
    tp=len(matched_events);fp=len(events)-tp;fn=len(truth)-tp
    return {'tp':tp,'fp':fp,'fn':fn,
            'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,
            'readable_matched':readable,'correct_plates':correct,
            'plate_exact_match':correct/readable if readable else None}
