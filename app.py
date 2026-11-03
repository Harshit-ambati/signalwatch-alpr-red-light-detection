import csv
import hashlib
import io
import json
from pathlib import Path
import cv2
import streamlit as st
from alpr.rules import parse_intervals
from alpr.pipeline import process

st.set_page_config(page_title='SignalWatch | Traffic review', page_icon='🚦', layout='wide')
st.markdown('''<style>.stApp {background:#0c1423;} h1 {letter-spacing:-1.5px;}
div[data-testid="stMetric"] {background:#172338;padding:18px;border-radius:12px;}
.block-container{padding-top:2rem;}</style>''', unsafe_allow_html=True)
st.caption('SIGNALWATCH / FINAL-YEAR PROJECT')
st.title('Traffic evidence, in one place.')
st.write('Analyze recorded traffic, inspect potential red-light crossings, and review plate readings.')
setup, review, guide = st.tabs(['Analyze video', 'Evidence review', 'Project guide'])

with setup:
    left,right = st.columns([1,1.8],gap='large')
    with left:
        upload = st.file_uploader('Upload footage', type=['mp4','avi','mov','mkv'])
        samples = list(Path('data/samples').glob('*.mp4')) if Path('data/samples').exists() else []
        sample = st.selectbox('Or choose a local sample', ['None']+[str(p) for p in samples],index=1 if samples else 0)
        source = None
        if upload:
            content = upload.getvalue()
            folder = Path('data/uploads'); folder.mkdir(parents=True,exist_ok=True)
            source = folder/(hashlib.sha256(content).hexdigest()[:20]+Path(upload.name).suffix.lower())
            if not source.exists(): source.write_bytes(content)
        elif sample != 'None': source = Path(sample)
        mode = st.selectbox('Signal source',['Visible traffic light','Manual timeline'])
        st.caption('Manual intervals are supplied labels, not automatic signal recognition. Outside them, state is unknown.')
        intervals_text = st.text_input('Red intervals in video seconds','5-15, 30-45', disabled=mode!='Manual timeline')
        preset = bool(source and not upload and source.name=='youtube.mp4')
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
                st.caption('Coordinates are percentages of the frame. Move the yellow line onto the actual stop line and the blue box around the signal for your monitored lane.')
                c1,c2 = st.columns(2)
                with c1:
                    x1 = st.slider('Line start X',0,100,5 if preset else 10); y1 = st.slider('Line start Y',0,100,64 if preset else 60)
                    rx1 = st.slider('Signal left',0,99,4 if preset else 80); ry1 = st.slider('Signal top',0,99,14 if preset else 5)
                with c2:
                    x2 = st.slider('Line end X',0,100,90); y2 = st.slider('Line end Y',0,100,54 if preset else 60)
                    rx2 = st.slider('Signal right',1,100,10 if preset else 95); ry2 = st.slider('Signal bottom',1,100,20 if preset else 30)
                h,w = frame.shape[:2]; preview=frame.copy()
                cv2.line(preview,(x1*w//100,y1*h//100),(x2*w//100,y2*h//100),(0,220,255),3)
                cv2.rectangle(preview,(rx1*w//100,ry1*h//100),(rx2*w//100,ry2*h//100),(255,150,0),2)
                st.image(preview,channels='BGR',use_container_width=True)
                st.caption('For the direction labels to apply, keep line start X smaller than line end X. Only vehicles crossing this finite segment are considered.')
        else:
            st.info('Upload a video to calibrate the camera. Your final recording can replace the sample later.')
            st.subheader('Reference demonstrations')
            st.video('https://www.youtube.com/watch?v=7UjyifjnzJg')
            st.caption('Reference playback only. Analysis requires a local video file; use original input footage when available.')
    if source and st.button('Analyze video',type='primary'):
        try:
            if x1 >= x2: raise ValueError('Line start X must be smaller than line end X.')
            if mode == 'Visible traffic light' and (rx1>=rx2 or ry1>=ry2): raise ValueError('Signal region must have positive width and height.')
            intervals = parse_intervals(intervals_text) if mode=='Manual timeline' else []
            if mode=='Manual timeline' and not intervals: raise ValueError('Enter at least one red interval.')
            if plate_model and not Path(plate_model).is_file(): raise ValueError('Plate model file does not exist.')
            config={'line':[[x1/100,y1/100],[x2/100,y2/100]],'roi':[rx1/100,ry1/100,rx2/100,ry2/100],
                    'direction':1 if direction=='Above to below' else -1,'signal_mode':mode,
                    'red_intervals':intervals,'ocr':ocr,'plate_model':plate_model or None,'max_seconds':limit}
            bar=st.progress(0); status=st.empty(); display=st.empty()
            def update(fraction,image,count):
                bar.progress(fraction);status.write(f'{count} potential violations recorded');display.image(image,channels='BGR')
            with st.spinner('Processing footage. First run downloads vehicle and OCR models…'):
                run=process(source,config,update)
            bar.progress(1.0);st.success(f'Analysis saved: {run.name}. Open Evidence review.')
        except Exception as exc:
            st.error(f'Analysis could not complete: {exc}')

with review:
    files=sorted(Path('data/runs').glob('*/results.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not files: st.info('Your completed analyses will appear here.')
    else:
        selected=st.selectbox('Analysis',files,format_func=lambda p:p.parent.name)
        data=json.loads(selected.read_text(encoding='utf-8'));events=data['events']
        a,b,c=st.columns(3)
        a.metric('Potential violations',len(events));b.metric('Plate candidates',sum(bool(e['plate']) for e in events));c.metric('Pending review',sum(e['review']=='pending' for e in events))
        st.caption(f"Status: {data['status']} · Source: {data['source']} · Signal: {data['config']['signal_mode']}")
        if data.get('error'):st.error(data['error'])
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
            with st.form(f'review-{selected.parent.name}-{event_id}'):
                corrected=st.text_input('Human-verified plate',value=event.get('corrected_plate',''))
                options=['pending','confirmed','rejected']
                decision=st.selectbox('Review decision',options,index=options.index(event['review']))
                if st.form_submit_button('Save review'):
                    event.update(review=decision,corrected_plate=corrected.strip().upper())
                    temp=selected.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2),encoding='utf-8');temp.replace(selected)
                    st.rerun()
        else:st.info('No potential violations recorded. Check calibration and signal visibility before interpreting this as a clean result.')
with guide:
    st.markdown('''### How it works
1. Upload a fixed-camera recording and calibrate its stop line and signal region.
2. YOLO detects vehicles; ByteTrack assigns temporary tracking IDs.
3. A bottom-center vehicle anchor must cross the line in the configured direction while both adjacent observations are red.
4. Candidate plate regions are read with OCR from several recent vehicle crops.
5. Evidence is saved locally for human review and CSV export.

### Current limitations
This is a research prototype. Color-based signal detection needs a tightly cropped signal region. Plate localization without a trained plate detector is a simple rectangular-region baseline. Tracking ID changes, occlusion, camera movement, and unreadable plates can produce misses or errors. Turning permissions and jurisdiction-specific rules are not modeled. No fines are issued.

### Video references
- [Red-light detection demonstration](https://www.youtube.com/watch?v=7UjyifjnzJg)
- [Traffic signal detection demonstration](https://www.youtube.com/watch?v=PxHkKLUk_QM)
- [Virtual-signal demonstration](https://www.youtube.com/watch?v=K5tCIU_1yP0)

Use original clips supplied by creators where possible. Demo playback is not proof of model accuracy. Evaluate on independently labelled footage before reporting results.
''')
