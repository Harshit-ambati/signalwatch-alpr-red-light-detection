"""Portable evidence bundles; restore uses an allowlist, never arbitrary ZIP paths."""
import io
import json
import re
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

IMAGE_NAME = re.compile(r'^[0-9]{4}/(before|crossing|vehicle|plate)\.jpg$')
MAX_BUNDLE_BYTES = 50 * 1024 * 1024


def export_run(folder):
    folder = Path(folder)
    output = io.BytesIO()
    with ZipFile(output, 'w') as archive:
        archive.write(folder/'results.json', arcname='results.json')
        for event in sorted(folder.iterdir()):
            if not event.is_dir() or not re.fullmatch(r'[0-9]{4}', event.name):
                continue
            for name in ('before.jpg', 'crossing.jpg', 'vehicle.jpg', 'plate.jpg'):
                image = event/name
                if image.is_file():
                    archive.write(image, arcname=f'{event.name}/{name}')
    return output.getvalue()


def restore_run(bundle, session_id, root=Path('data/runs')):
    if len(bundle) > MAX_BUNDLE_BYTES:
        raise ValueError('Evidence bundle exceeds 50 MB.')
    try:
        with ZipFile(io.BytesIO(bundle)) as archive:
            files = archive.infolist()
            if not files or len(files) > 1000 or sum(item.file_size for item in files) > MAX_BUNDLE_BYTES:
                raise ValueError('Evidence bundle is too large or empty.')
            names = [item.filename for item in files]
            if len(names) != len(set(names)) or 'results.json' not in names or any(
                item.is_dir() or (name != 'results.json' and not IMAGE_NAME.fullmatch(name))
                for item, name in zip(files, names)
            ):
                raise ValueError('Evidence bundle contains unexpected files.')
            manifest = json.loads(archive.read('results.json'))
            if not isinstance(manifest, dict) or not isinstance(manifest.get('events'), list) or not isinstance(manifest.get('config'), dict):
                raise ValueError('Evidence bundle has an invalid results file.')
            event_ids = {event.get('id') for event in manifest['events'] if isinstance(event, dict)}
            if len(event_ids) != len(manifest['events']) or any(not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}', value) for value in event_ids):
                raise ValueError('Evidence bundle has invalid event IDs.')
            if any(name != 'results.json' and name[:4] not in event_ids for name in names):
                raise ValueError('Evidence bundle has unmatched images.')
            target = Path(root)/uuid4().hex[:12]
            target.mkdir(parents=True)
            manifest['id'] = target.name
            manifest['config']['review_session_id'] = session_id
            for name in names:
                if name == 'results.json':
                    continue
                dest = target/name
                dest.parent.mkdir(exist_ok=True)
                dest.write_bytes(archive.read(name))
            (target/'results.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            return target
    except (BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('This is not a valid SignalWatch evidence bundle.') from exc
