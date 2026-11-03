from streamlit.testing.v1 import AppTest
from pathlib import Path
import json


def test_empty_dashboard_renders(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SIGNALWATCH_PASSWORD','test-only-password')
    app=AppTest.from_file(str(entry))
    app.session_state['authenticated']=True
    app.run(timeout=30)
    assert not app.exception
    assert app.title[0].value=='Traffic evidence, in one place.'
    assert len(app.tabs)==4


def test_review_is_saved(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SIGNALWATCH_PASSWORD','test-only-password')
    folder=tmp_path/'data/runs/test';folder.mkdir(parents=True)
    result=folder/'results.json'
    app=AppTest.from_file(str(entry))
    app.session_state['authenticated']=True
    app.run(timeout=30)
    session_id=app.session_state['review_session_id']
    result.write_text(json.dumps({'status':'complete','source':'fixture.avi','config':{'signal_mode':'Manual timeline','review_session_id':session_id},
        'events':[{'id':'0001','track_id':1,'video_seconds':1,'plate':'','review':'pending','corrected_plate':''}]}))
    app.run(timeout=30)
    assert not app.exception
    next(x for x in app.text_input if x.label=='Human-verified plate').set_value('TEST123')
    next(x for x in app.selectbox if x.label=='Review decision').select('confirmed')
    next(x for x in app.button if x.label=='Save review').click()
    app.run(timeout=30)
    assert not app.exception
    saved=json.loads(result.read_text())['events'][0]
    assert saved['corrected_plate']=='TEST123'
    assert saved['review']=='confirmed'


def test_other_session_evidence_is_hidden(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SIGNALWATCH_PASSWORD','test-only-password')
    folder=tmp_path/'data/runs/private';folder.mkdir(parents=True)
    (folder/'results.json').write_text(json.dumps({'status':'complete','source':'private.avi',
        'config':{'signal_mode':'Manual timeline','review_session_id':'another-session'},'events':[]}))
    app=AppTest.from_file(str(entry))
    app.session_state['authenticated']=True
    app.run(timeout=30)
    assert not app.exception
    assert not any(select.label=='Analysis' for select in app.selectbox)


def test_password_gate(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SIGNALWATCH_PASSWORD','test-only-password')
    app=AppTest.from_file(str(entry)).run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==0
    next(x for x in app.text_input if x.label=='Access password').set_value('test-only-password')
    next(x for x in app.button if x.label=='Unlock app').click()
    app.run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==4


def test_missing_password_blocks_app(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('SIGNALWATCH_PASSWORD',raising=False)
    app=AppTest.from_file(str(entry)).run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==0
