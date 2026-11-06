import csv
import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile
import cv2
import streamlit as st
from alpr.auth import configured_password, password_matches
from alpr.bundle import export_run, restore_run
from alpr.evaluate import evaluate, read_ground_truth
from alpr.rules import parse_intervals
from alpr.pipeline import process
from alpr.calibration import suggest_geometry
from alpr.video_source import download_youtube

st.set_page_config(page_title='SignalWatch | Traffic review', page_icon='🚦', layout='wide')
st.markdown('''<style>.stApp {background:#0c1423;} h1 {letter-spacing:-1.5px;}
div[data-testid="stMetric"] {background:#172338;padding:18px;border-radius:12px;}
.block-container{padding-top:2rem;}</style>''', unsafe_allow_html=True)
st.caption('SIGNALWATCH / FINAL-YEAR PROJECT')
st.title('Traffic evidence, in one place.')
st.write('Analyze recorded traffic, inspect potential red-light crossings, and review plate readings.')
expected_password = configured_password(st.secrets)
if not expected_password:
    st.error('Access is not configured. Set APP_PASSWORD in Streamlit Cloud secrets before using this app.')
    st.stop()
if not st.session_state.get('authenticated', False):
    with st.form('login'):
        password = st.text_input('Access password', type='password')
        submitted = st.form_submit_button('Unlock app')
    if submitted:
        if password_matches(password, expected_password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error('Incorrect password.')
    st.stop()
if 'review_session_id' not in st.session_state:
    st.session_state.review_session_id = uuid4().hex
setup, review, evaluation, guide = st.tabs(['Analyze video', 'Evidence review', 'Evaluate', 'Project guide'])

with setup:
    left,right = st.columns([1,1.8],gap='large')
    with left:
        input_kind = st.radio('Video source', ['Upload file', 'YouTube link', 'Local sample'], horizontal=True)
        upload = st.file_uploader('Upload footage', type=['mp4','avi','mov','mkv']) if input_kind == 'Upload file' else None
        samples = list(Path('data/samples').glob('*.mp4')) if Path('data/samples').exists() else []
        sample = st.selectbox('Local sample', ['None']+[str(p) for p in samples],index=1 if samples else 0) if input_kind == 'Local sample' else 'None'
        if input_kind == 'YouTube link':
            url = st.text_input('Public YouTube video URL', placeholder='https://www.youtube.com/watch?v=...')
            if st.button('Import YouTube video'):
                try:
                    with st.spinner('Downloading a short MP4 for analysis…'):
                        imported = download_youtube(url)
                    st.session_state.youtube_source = str(imported)
                    st.session_state.youtube_url = url.strip()
                    st.success('Video imported. Review the proposed geometry before analysis.')
                except Exception as exc:
                    st.error(f'Import failed: {exc}')
            st.caption('Finished public recordings only, up to 10 minutes and 100 MB. Import may fail when YouTube restricts automated access.')
        source = None
        if upload:
            content = upload.getvalue()
            folder = Path('data/uploads'); folder.mkdir(parents=True,exist_ok=True)
            source = folder/(hashlib.sha256(content).hexdigest()[:20]+Path(upload.name).suffix.lower())
            if not source.exists(): source.write_bytes(content)
        elif input_kind == 'YouTube link' and url.strip() == st.session_state.get('youtube_url'):
            source = Path(st.session_state.youtube_source)
            if not source.is_file(): source = None
        elif sample != 'None': source = Path(sample)
        mode = st.selectbox('Signal source',['Visible traffic light','Manual timeline'])
        st.caption('Manual intervals are supplied labels, not automatic signal recognition. Outside them, state is unknown.')
        intervals_text = st.text_input('Red intervals in video seconds','5-15, 30-45', disabled=mode!='Manual timeline')
        preset = bool(source and source.name=='youtube.mp4')
        if preset:
            st.caption('Development sample: 5.16 seconds, 352 × 288. Preset geometry is approximate; plates are too small for dependable recognition.')
        direction = st.selectbox('Crossing direction',['Above to below','Below to above'],index=1 if preset else 0)
        ocr = st.checkbox('Read license plates',value=True)
        st.caption('Default plate localization is experimental. Unreadable plates stay blank; all OCR needs review.')
        plate_model = st.text_input('Optional trained plate detector (.pt file)','')
        limit = st.number_input('Analyze first N seconds (0 = entire video)',min_value=0,value=60)
    with right:
        if source:
            cap = cv2.VideoCapture(str(source)); ok,frame = cap.read(); cap.release()
            if not ok:
                st.error('This file could not be decoded. Try an MP4 encoded with H.264.')
                source = None
            else:
                st.subheader('Calibrate this camera')
                st.caption('The app suggests a stop line and signal location from the frame. Check both before analysis; colored lights and road markings can cause wrong suggestions.')
                st.caption('This detector assumes a fixed camera. On a moving dashcam, the signal and stop line shift during the clip and fixed coordinates cannot give reliable violation results.')
                source_key = f'{source.resolve()}:{source.stat().st_size}'
                geometry = suggest_geometry(frame)
                keys = ['line_x1','line_y1','line_x2','line_y2','signal_x1','signal_y1','signal_x2','signal_y2']
                proposed = [max(0, min(100, round(value * 100))) for value in
                            geometry['line'][0] + geometry['line'][1] + geometry['roi']]
                proposed[4] = min(99, proposed[4]); proposed[5] = min(99, proposed[5])
                proposed[6] = max(1, proposed[6]); proposed[7] = max(1, proposed[7])
                if st.session_state.get('geometry_source') != source_key:
                    st.session_state.geometry_source = source_key
                    for key, value in zip(keys, proposed):
                        st.session_state[key] = value
                if st.button('Suggest coordinates again'):
                    for key, value in zip(keys, proposed):
                        st.session_state[key] = value
                    st.rerun()
                if not geometry['line_found']:
                    st.warning('No clear road line was found. Position the yellow line manually.')
                if mode == 'Visible traffic light' and not geometry['signal_found']:
                    st.warning('No clear signal light was found. Position the blue box manually.')
                st.caption('Coordinates are percentages of the frame. The yellow line must match the stop line; the blue box must include only the signal for the monitored lane.')
                c1,c2 = st.columns(2)
                with c1:
                    x1 = st.slider('Line start X',0,100,key='line_x1'); y1 = st.slider('Line start Y',0,100,key='line_y1')
                    rx1 = st.slider('Signal left',0,99,key='signal_x1'); ry1 = st.slider('Signal top',0,99,key='signal_y1')
                with c2:
                    x2 = st.slider('Line end X',0,100,key='line_x2'); y2 = st.slider('Line end Y',0,100,key='line_y2')
                    rx2 = st.slider('Signal right',1,100,key='signal_x2'); ry2 = st.slider('Signal bottom',1,100,key='signal_y2')
                h,w = frame.shape[:2]; preview=frame.copy()
                cv2.line(preview,(x1*w//100,y1*h//100),(x2*w//100,y2*h//100),(0,220,255),3)
                cv2.rectangle(preview,(rx1*w//100,ry1*h//100),(rx2*w//100,ry2*h//100),(255,150,0),2)
                st.image(preview,channels='BGR',use_container_width=True)
                st.caption('For the direction labels to apply, keep line start X smaller than line end X. Only vehicles crossing this finite segment are considered.')
        else:
            st.info('Choose a video source to calibrate the camera. Your final recording can replace the sample later.')
    if source and st.button('Analyze video',type='primary'):
        try:
            if x1 >= x2: raise ValueError('Line start X must be smaller than line end X.')
            if mode == 'Visible traffic light' and (rx1>=rx2 or ry1>=ry2): raise ValueError('Signal region must have positive width and height.')
            if mode == 'Visible traffic light' and not geometry['signal_found'] and [rx1,ry1,rx2,ry2] == proposed[4:]:
                raise ValueError('No traffic light was found automatically. Position the blue signal box manually before analyzing.')
            intervals = parse_intervals(intervals_text) if mode=='Manual timeline' else []
            if mode=='Manual timeline' and not intervals: raise ValueError('Enter at least one red interval.')
            if plate_model and not Path(plate_model).is_file(): raise ValueError('Plate model file does not exist.')
            config={'line':[[x1/100,y1/100],[x2/100,y2/100]],'roi':[rx1/100,ry1/100,rx2/100,ry2/100],
                    'direction':1 if direction=='Above to below' else -1,'signal_mode':mode,
                    'red_intervals':intervals,'ocr':ocr,'plate_model':plate_model or None,
                    'max_seconds':limit,'review_session_id':st.session_state.review_session_id}
            bar=st.progress(0); status=st.empty(); display=st.empty()
            def update(fraction,image,count):
                bar.progress(fraction);status.write(f'{count} potential violations recorded');display.image(image,channels='BGR')
            with st.spinner('Processing footage. First run downloads vehicle and OCR models…'):
                run=process(source,config,update)
            bar.progress(1.0);st.success(f'Analysis saved: {run.name}. Open Evidence review.')
        except Exception as exc:
            st.error(f'Analysis could not complete: {exc}')

with review:
    restore_file=st.file_uploader('Restore an evidence bundle',type=['zip'])
    if restore_file and st.button('Restore evidence'):
        try:
            restored=restore_run(restore_file.getvalue(),st.session_state.review_session_id)
            st.success(f'Restored analysis {restored.name}.')
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    files=[]
    for candidate in Path('data/runs').glob('*/results.json'):
        try:
            details=json.loads(candidate.read_text(encoding='utf-8'))
            if details.get('config',{}).get('review_session_id')==st.session_state.review_session_id:
                files.append(candidate)
        except (OSError, json.JSONDecodeError):
            continue
    files.sort(key=lambda p:p.stat().st_mtime,reverse=True)
    if not files: st.info('Analyses from this browser session will appear here. Export evidence before closing the session.')
    else:
        selected=st.selectbox('Analysis',files,format_func=lambda p:p.parent.name)
        data=json.loads(selected.read_text(encoding='utf-8'));events=data['events']
        a,b,c=st.columns(3)
        a.metric('Potential violations',len(events));b.metric('Plate candidates',sum(bool(e['plate']) for e in events));c.metric('Pending review',sum(e['review']=='pending' for e in events))
        st.caption(f"Status: {data['status']} · Source: {data['source']} · Signal: {data['config']['signal_mode']}")
        if data.get('error'):st.error(data['error'])
        st.download_button('Download complete evidence bundle',export_run(selected.parent),
                           f'signalwatch-{selected.parent.name}.zip','application/zip')
        if events:
            st.dataframe(events,use_container_width=True)
            export=io.StringIO();writer=csv.DictWriter(export,fieldnames=events[0].keys());writer.writeheader();writer.writerows(events)
            st.download_button('Export event CSV',export.getvalue(),'events.csv','text/csv')
            event_id=st.selectbox('Inspect evidence',[e['id'] for e in events])
            event=next(e for e in events if e['id']==event_id);folder=selected.parent/event_id
            columns=st.columns(3)
            for col,name,label in zip(columns,['before.jpg','crossing.jpg','plate.jpg'],['Before crossing','Crossing evidence','Plate candidate']):
                if (folder/name).exists():col.image(str(folder/name),caption=label,use_container_width=True)
                else:col.info(f'{label}: unavailable')
            evidence=io.BytesIO()
            with ZipFile(evidence,'w') as archive:
                for name in ['before.jpg','crossing.jpg','vehicle.jpg','plate.jpg']:
                    item=folder/name
                    if item.is_file():archive.write(item,arcname=name)
            st.download_button('Download event evidence',evidence.getvalue(),f'evidence-{event_id}.zip','application/zip')
            with st.form(f'review-{selected.parent.name}-{event_id}'):
                corrected=st.text_input('Human-verified plate',value=event.get('corrected_plate',''))
                options=['pending','confirmed','rejected']
                decision=st.selectbox('Review decision',options,index=options.index(event['review']))
                if st.form_submit_button('Save review'):
                    event.update(review=decision,corrected_plate=corrected.strip().upper())
                    temp=selected.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2),encoding='utf-8');temp.replace(selected)
                    st.rerun()
        else:
            st.info('No potential violations recorded. Check calibration and signal visibility before interpreting this as a clean result.')
            diagnostics=data.get('diagnostics',{})
            if diagnostics:
                counts=diagnostics.get('signal_frames',{})
                st.write(f"Signal frames: {counts.get('red',0)} red, {counts.get('green',0)} green, "
                         f"{counts.get('amber',0)} amber, {counts.get('unknown',0)} unknown. "
                         f"Vehicle crossings of the selected line: {diagnostics.get('line_crossings',0)}.")
                if not counts.get('red'):
                    st.warning('The selected signal box was never classified as red. Check that it follows the correct light throughout the clip.')
                if not diagnostics.get('line_crossings'):
                    st.warning('No tracked vehicle crossed the selected line segment. Check the line position, direction, and camera movement.')
with evaluation:
    st.write('Compare saved detections with manually labelled red-light crossings from the same video.')
    available=[]
    for candidate in Path('data/runs').glob('*/results.json'):
        try:
            record=json.loads(candidate.read_text(encoding='utf-8'))
            if record.get('status')=='complete' and record.get('config',{}).get('review_session_id')==st.session_state.review_session_id:
                available.append(candidate)
        except (OSError,json.JSONDecodeError):
            continue
    if available:
        chosen=st.selectbox('Run to evaluate',available,format_func=lambda p:p.parent.name)
        labels=st.file_uploader('Ground truth CSV',type=['csv'])
        st.caption('CSV columns: video_seconds,plate. Include one row per true red-light crossing. Leave plate blank when unreadable.')
        if labels:
            try:
                truth=read_ground_truth(labels.getvalue().decode('utf-8-sig'))
                result=evaluate(json.loads(chosen.read_text(encoding='utf-8'))['events'],truth)
                c1,c2,c3=st.columns(3)
                c1.metric('Correctly matched',result['tp'])
                c2.metric('False alarms',result['fp'])
                c3.metric('Missed crossings',result['fn'])
                st.write({key:round(value,3) if isinstance(value,float) else value for key,value in result.items()})
            except (ValueError,UnicodeDecodeError) as exc:
                st.error(str(exc))
    else:
        st.info('Analyze or restore a run to evaluate it.')
with guide:
    st.markdown('''### How it works
1. Upload a fixed-camera recording or import a public YouTube video. Check the suggested stop line and signal region.
2. YOLO detects vehicles; ByteTrack assigns temporary tracking IDs.
3. A bottom-center vehicle anchor must cross the line in the configured direction while both adjacent observations are red.
4. Candidate plate regions are read with OCR from several recent vehicle crops.
5. Evidence is saved locally for human review and CSV export.

### Current limitations
This is a research prototype. Color-based signal detection needs a tightly cropped signal region. Plate localization without a trained plate detector is a simple rectangular-region baseline. Tracking ID changes, occlusion, camera movement, and unreadable plates can produce misses or errors. Turning permissions and jurisdiction-specific rules are not modeled. No fines are issued.

### Video references
- [Traffic signal detection demonstration](https://www.youtube.com/watch?v=PxHkKLUk_QM)
- [Virtual-signal demonstration](https://www.youtube.com/watch?v=K5tCIU_1yP0)

Use original clips supplied by creators where possible. Demo playback is not proof of model accuracy. Evaluate on independently labelled footage before reporting results.
''')
