"""Pinned optional model assets downloaded only when selected."""
import hashlib
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4


PLATE_MODEL_URL = ('https://huggingface.co/Koushim/yolov8-license-plate-detection/'
                   'resolve/83c98fbe7412fe8b3950adb5637cfd08b0f04809/best.pt')
PLATE_MODEL_SHA256 = '2d95861825bb4184404344c9cf809f40fd31dba785fe54e8ba5b9a3583789822'
PLATE_MODEL_PATH = Path('models/license_plate_yolov8n.pt')
MAX_MODEL_BYTES = 15_000_000


def _matches(path):
    if not path.is_file():
        return False
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest() == PLATE_MODEL_SHA256


def ensure_plate_model():
    """Return a verified local checkpoint, downloading it on first use."""
    path = PLATE_MODEL_PATH
    if _matches(path):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'{path.name}.{uuid4().hex}.tmp')
    try:
        size = 0
        with urlopen(PLATE_MODEL_URL, timeout=60) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_MODEL_BYTES:
                    raise ValueError('Plate model download exceeded the expected size.')
                output.write(chunk)
        if not _matches(temporary):
            raise ValueError('Plate model checksum did not match the published checkpoint.')
        temporary.replace(path)
        return path
    finally:
        temporary.unlink(missing_ok=True)
