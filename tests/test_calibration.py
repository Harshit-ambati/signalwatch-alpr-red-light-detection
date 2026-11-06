import cv2
import numpy as np

from alpr.calibration import suggest_geometry
from alpr.video_source import download_youtube, youtube_id


def test_suggests_visible_line_and_signal():
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    cv2.line(frame, (30, 125), (270, 125), (255, 255, 255), 3)
    cv2.circle(frame, (260, 30), 5, (0, 0, 255), -1)
    result = suggest_geometry(frame)
    assert result['line_found']
    assert result['signal_found']
    assert abs(result['line'][0][1] - .625) < .05
    assert result['roi'][0] < 260 / 300 < result['roi'][2]


def test_blank_frame_requires_manual_geometry():
    result = suggest_geometry(np.zeros((200, 300, 3), dtype=np.uint8))
    assert not result['line_found']
    assert not result['signal_found']


def test_youtube_links_are_restricted_to_video_ids():
    assert youtube_id('https://www.youtube.com/watch?v=7UjyifjnzJg&t=2') == '7UjyifjnzJg'
    assert youtube_id('https://youtu.be/7UjyifjnzJg') == '7UjyifjnzJg'
    for url in ['http://youtube.com/watch?v=7UjyifjnzJg',
                'https://youtube.com.evil.test/watch?v=7UjyifjnzJg',
                'https://www.youtube.com/playlist?list=123']:
        try:
            youtube_id(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Accepted unsafe or unsupported link: {url}')


def test_youtube_import_checks_duration_before_download(tmp_path, monkeypatch):
    import yt_dlp

    class FakeDownloader:
        def __init__(self, options):
            self.options = options

        def __enter__(self): return self
        def __exit__(self, *_): return False
        def extract_info(self, *_args, **_kwargs): return {'duration': 601, 'is_live': False}
        def download(self, *_): raise AssertionError('Oversized duration must not download')

    monkeypatch.setattr(yt_dlp, 'YoutubeDL', FakeDownloader)
    try:
        download_youtube('https://youtu.be/7UjyifjnzJg', tmp_path)
    except ValueError as exc:
        assert '10 minute' in str(exc)
    else:
        raise AssertionError('Accepted a video longer than the limit')
    assert not list(tmp_path.iterdir())
