import io
import json
from zipfile import ZipFile
import pytest
from alpr.bundle import export_run, restore_run


def test_export_restore_preserves_reviews_and_rebinds_session(tmp_path):
    source=tmp_path/'source';(source/'0001').mkdir(parents=True)
    (source/'0001'/'crossing.jpg').write_bytes(b'jpg')
    (source/'results.json').write_text(json.dumps({'id':'source','status':'complete',
        'config':{'review_session_id':'old'},'events':[{'id':'0001','review':'confirmed','corrected_plate':'ABC123'}]}))
    restored=restore_run(export_run(source),'new-session',tmp_path/'runs')
    result=json.loads((restored/'results.json').read_text())
    assert result['config']['review_session_id']=='new-session'
    assert result['events'][0]['corrected_plate']=='ABC123'
    assert (restored/'0001'/'crossing.jpg').read_bytes()==b'jpg'


def test_restore_rejects_traversal(tmp_path):
    output=io.BytesIO()
    with ZipFile(output,'w') as archive:
        archive.writestr('results.json',json.dumps({'events':[],'config':{}}))
        archive.writestr('../escape.txt','unsafe')
    with pytest.raises(ValueError,match='unexpected files'):
        restore_run(output.getvalue(),'session',tmp_path/'runs')
    assert not (tmp_path/'escape.txt').exists()
