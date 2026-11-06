"""Import a bounded, public YouTube recording for local analysis."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

MAX_BYTES = 100 * 1024 * 1024
MAX_DURATION = 10 * 60


def youtube_id(url):
    parsed = urlparse(url.strip())
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port:
        raise ValueError('Use a public HTTPS YouTube video link.')
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'} and parsed.path == '/watch':
        candidate = parse_qs(parsed.query).get('v', [''])[0]
    elif host == 'youtu.be':
        candidate = parsed.path.strip('/')
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'} and parsed.path.startswith('/shorts/'):
        candidate = parsed.path.split('/')[2]
    else:
        raise ValueError('Use a YouTube watch, Shorts, or youtu.be video link.')
    if len(candidate) != 11 or not all(c.isalnum() or c in '-_' for c in candidate):
        raise ValueError('The YouTube video ID is invalid.')
    return candidate


def download_youtube(url, directory=Path('data/uploads')):
    from yt_dlp import YoutubeDL

    video_id = youtube_id(url)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / f'youtube-{video_id}.mp4'
    if output.is_file() and 0 < output.stat().st_size <= MAX_BYTES:
        return output

    def check_size(status):
        if status.get('downloaded_bytes', 0) > MAX_BYTES:
            raise ValueError('YouTube video exceeds the 100 MB import limit.')

    options = {
        'format': 'best[ext=mp4][height<=480][filesize<100M]/best[ext=mp4][height<=480]',
        'outtmpl': str(output), 'noplaylist': True, 'quiet': True, 'no_warnings': True,
        'overwrites': True, 'max_filesize': MAX_BYTES, 'progress_hooks': [check_size],
        'socket_timeout': 20, 'retries': 2, 'fragment_retries': 2,
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            if info.get('is_live') or info.get('live_status') in {'is_live', 'is_upcoming'}:
                raise ValueError('Live streams are not supported by this importer; use a finished recording.')
            if info.get('duration') and info['duration'] > MAX_DURATION:
                raise ValueError('YouTube video exceeds the 10 minute import limit.')
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
        if not output.is_file() or not 0 < output.stat().st_size <= MAX_BYTES:
            raise ValueError('No usable MP4 was downloaded within the 100 MB limit.')
    except Exception:
        output.unlink(missing_ok=True)
        for partial in directory.glob(f'youtube-{video_id}.mp4.part*'):
            partial.unlink(missing_ok=True)
        raise
    return output
