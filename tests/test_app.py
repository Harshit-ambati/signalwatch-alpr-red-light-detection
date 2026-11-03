from streamlit.testing.v1 import AppTest
from pathlib import Path
import json


def test_empty_dashboard_renders(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_file(str(entry)).run(timeout=30)
    assert not app.exception
    assert app.title[0].value=='Traffic evidence, in one place.'
    assert len(app.tabs)==3


def test_review_is_saved(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    folder=tmp_path/'data/runs/test';folder.mkdir(parents=True)
    result=folder/'results.json'
    result.write_text(json.dumps({'status':'complete','source':'fixture.avi','config':{'signal_mode':'Manual timeline'},
        'events':[{'id':'0001','track_id':1,'video_seconds':1,'plate':'','review':'pending','corrected_plate':''}]}))
    app=AppTest.from_file(str(entry)).run(timeout=30)
    assert not app.exception
    next(x for x in app.text_input if x.label=='Human-verified plate').set_value('TEST123')
    next(x for x in app.selectbox if x.label=='Review decision').select('confirmed')
    next(x for x in app.button if x.label=='Save review').click()
    app.run(timeout=30)
    assert not app.exception
    saved=json.loads(result.read_text())['events'][0]
    assert saved['corrected_plate']=='TEST123'
    assert saved['review']=='confirmed'
