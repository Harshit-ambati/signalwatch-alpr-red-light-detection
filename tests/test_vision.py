import cv2
import numpy as np
import pytest
from alpr.vision import signal_state

@pytest.mark.parametrize('color,state',[((0,0,255),'red'),((0,255,0),'green'),((0,200,255),'amber'),((0,0,0),'unknown')])
def test_signal_colors(color,state):
    frame=np.zeros((100,100,3),dtype=np.uint8)
    cv2.circle(frame,(50,50),15,color,-1)
    assert signal_state(frame,(0,0,1,1))==state

def test_empty_region_unknown():
    assert signal_state(np.zeros((20,20,3),dtype=np.uint8),(0,0,0,0))=='unknown'
