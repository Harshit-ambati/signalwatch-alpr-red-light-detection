"""Integration test with controlled tracks; does not measure detector accuracy."""
import json
from types import SimpleNamespace
import cv2
import numpy as np
from alpr.pipeline import box_iou, process


class Tensor:
    def __init__(self,data): self.data=data
    def cpu(self): return self
    def int(self): return self
    def tolist(self): return self.data


def test_duplicate_vehicle_boxes_have_high_overlap():
    assert box_iou([0, 0, 100, 100], [2, 1, 101, 99]) > .7
    assert box_iou([0, 0, 100, 100], [110, 0, 210, 100]) == 0


def test_pipeline_persists_crossing_and_evidence(tmp_path,monkeypatch):
    import ultralytics
    monkeypatch.chdir(tmp_path)
    video=tmp_path/'test.avi'
    writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),10,(200,200))
    assert writer.isOpened()
    for _ in range(5):writer.write(np.zeros((200,200,3),dtype=np.uint8))
    writer.release()
    class Detector:
        def __init__(self,*args):self.frame=0
        def track(self,*args,**kwargs):
            bottom=80+self.frame*10;self.frame+=1
            same_vehicle=[80,bottom-30,120,bottom]
            return [SimpleNamespace(boxes=SimpleNamespace(id=Tensor([1,2]),xyxy=Tensor([same_vehicle,same_vehicle])))]
    monkeypatch.setattr(ultralytics,'YOLO',Detector)
    config={'line':[[.2,.5],[.8,.5]],'direction':1,'ocr':False,'signal_mode':'Manual timeline','red_intervals':[[0,1]],'max_seconds':0}
    run=process(video,config)
    result=json.loads((run/'results.json').read_text())
    assert result['status']=='complete'
    assert len(result['events'])==1
    assert result['events'][0]['plate']==''
    assert result['events'][0]['video_seconds']==.2
    assert result['diagnostics']['signal_frames']['red']==5
    assert result['diagnostics']['line_crossings']==2
    assert (run/'0001'/'before.jpg').is_file()
    assert (run/'0001'/'crossing.jpg').is_file()


def test_unreadable_video_does_not_create_completed_run(tmp_path,monkeypatch):
    import pytest
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError,match='Cannot decode'):
        process(tmp_path/'missing.mp4',{})
