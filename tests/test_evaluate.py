from alpr.evaluate import evaluate, read_ground_truth


def test_matches_unique_events_and_plate_accuracy():
    truth=read_ground_truth('video_seconds,plate\n1.0,ABC 123\n3.0,\n5.0,XYZ999\n')
    events=[{'video_seconds':1.1,'plate':'ABC123','corrected_plate':'WRONG'},
            {'video_seconds':1.2,'plate':'DUPLICATE'},
            {'video_seconds':3.1,'plate':''}]
    result=evaluate(events,truth)
    assert (result['tp'],result['fp'],result['fn'])==(2,1,1)
    assert result['precision']==2/3
    assert result['recall']==2/3
    assert result['plate_exact_match']==1
