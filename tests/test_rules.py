from alpr.rules import CrossingDetector, parse_intervals
import pytest

def test_red_crossing_is_reported_once():
    rule=CrossingDetector((0.2,0.5),(0.8,0.5))
    assert not rule.update(1,(0.5,0.4),0,'red')
    assert rule.update(1,(0.5,0.6),0.1,'red')
    rule.update(1,(0.5,0.4),0.2,'red')
    assert not rule.update(1,(0.5,0.6),0.3,'red')

@pytest.mark.parametrize('previous,current,x,gap', [('green','red',.5,.1),('red','green',.5,.1),('unknown','red',.5,.1),('red','red',.9,.1),('red','red',.5,1)])
def test_nonviolations(previous,current,x,gap):
    rule=CrossingDetector((.2,.5),(.8,.5))
    rule.update(1,(x,.4),0,previous)
    assert not rule.update(1,(x,.6),gap,current)

def test_already_beyond_and_reverse():
    rule=CrossingDetector((.2,.5),(.8,.5))
    assert not rule.update(1,(.5,.6),0,'red')
    assert not rule.update(1,(.5,.4),.1,'red')

def test_reverse_configured():
    rule=CrossingDetector((.2,.5),(.8,.5),direction=-1)
    rule.update(1,(.5,.6),0,'red')
    assert rule.update(1,(.5,.4),.1,'red')

def test_intervals():
    assert parse_intervals('1-2, 3-5')==[(1,2),(3,5)]
    with pytest.raises(ValueError):parse_intervals('5-2')


def test_approach_lane_allows_forward_vehicle():
    rule = CrossingDetector((.2, .5), (.8, .5), direction=-1,
                            approach_zone=(.3, .55, .7, 1))
    assert not rule.update(1, (.5, .8), 0, 'red')
    assert not rule.update(1, (.5, .7), .1, 'red')
    assert rule.update(1, (.5, .45), .2, 'red')


def test_approach_lane_rejects_side_traffic():
    rule = CrossingDetector((.2, .5), (.8, .5), direction=-1,
                            approach_zone=(.3, .55, .7, 1))
    rule.update(1, (.85, .58), 0, 'red')
    rule.update(1, (.75, .57), .1, 'red')
    assert not rule.update(1, (.65, .49), .2, 'red')


def test_approach_lane_rejects_lateral_drift():
    rule = CrossingDetector((.2, .5), (.8, .5), direction=-1,
                            approach_zone=(.2, .55, .8, 1))
    rule.update(1, (.7, .57), 0, 'red')
    rule.update(1, (.6, .56), .1, 'red')
    assert not rule.update(1, (.5, .49), .2, 'red')


def test_approach_lane_rejects_crossing_outside_lane_width():
    rule = CrossingDetector((.2, .5), (.9, .5), direction=-1,
                            approach_zone=(.3, .55, .8, 1))
    rule.update(1, (.7, .7), 0, 'red')
    rule.update(1, (.77, .6), .1, 'red')
    assert not rule.update(1, (.86, .45), .2, 'red')
