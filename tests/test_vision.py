import cv2
import numpy as np
import pytest
from alpr.vision import PlateReader, signal_state, select_plate_read

@pytest.mark.parametrize('color,state',[((0,0,255),'red'),((0,255,0),'green'),((0,200,255),'amber'),((0,0,0),'unknown')])
def test_signal_colors(color,state):
    frame=np.zeros((100,100,3),dtype=np.uint8)
    cv2.circle(frame,(50,50),15,color,-1)
    assert signal_state(frame,(0,0,1,1))==state

def test_empty_region_unknown():
    assert signal_state(np.zeros((20,20,3),dtype=np.uint8),(0,0,0,0))=='unknown'


def test_compressed_red_signal_hue():
    # A real compressed red lamp can fall below the old upper-red cutoff of 170.
    red = cv2.cvtColor(np.uint8([[[168, 248, 180]]]), cv2.COLOR_HSV2BGR)[0, 0]
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(frame, (50, 50), 15, tuple(int(value) for value in red), -1)
    assert signal_state(frame, (0, 0, 1, 1)) == 'red'


def test_plate_read_prefers_consensus_over_one_confident_error():
    reads = [('KW527', .57, 'first'), ('KH527', .92, 'wrong'),
             ('KW527', .64, 'second')]
    assert select_plate_read(reads) == ('KW527', .64, 'second')
    assert select_plate_read([]) is None


def test_plate_ocr_keeps_margin_around_detector_box():
    class Boxes:
        def cpu(self): return self
        def tolist(self): return [[10,10,110,40]]
    class Detector:
        def __call__(self,*args,**kwargs):
            return [type('Result',(),{'boxes':type('BoxSet',(),{'xyxy':Boxes()})()})()]
    class OCR:
        def readtext(self,image,**kwargs):
            return [(None,'ABC123',.9)] if image.shape[0] > 90 else []
    reader=PlateReader.__new__(PlateReader)
    reader.detector=Detector()
    reader.reader=OCR()
    result=reader.read(np.zeros((150,150,3),dtype=np.uint8))
    assert result[0]=='ABC123'
    assert result[2].shape[0] > 30
