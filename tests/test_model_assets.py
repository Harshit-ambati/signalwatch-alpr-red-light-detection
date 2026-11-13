import hashlib
import io

import pytest

from alpr import model_assets


def test_model_download_verifies_checksum(tmp_path, monkeypatch):
    payload = b'plate-model-test'
    path = tmp_path / 'models' / 'plate.pt'
    monkeypatch.setattr(model_assets, 'PLATE_MODEL_PATH', path)
    monkeypatch.setattr(model_assets, 'PLATE_MODEL_SHA256', hashlib.sha256(payload).hexdigest())
    calls = []

    def download(url, timeout):
        calls.append((url, timeout))
        return io.BytesIO(payload)

    monkeypatch.setattr(model_assets, 'urlopen', download)
    assert model_assets.ensure_plate_model() == path
    assert path.read_bytes() == payload
    assert model_assets.ensure_plate_model() == path
    assert len(calls) == 1


def test_model_download_rejects_wrong_hash(tmp_path, monkeypatch):
    path = tmp_path / 'models' / 'plate.pt'
    monkeypatch.setattr(model_assets, 'PLATE_MODEL_PATH', path)
    monkeypatch.setattr(model_assets, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'wrong'))
    with pytest.raises(ValueError, match='checksum'):
        model_assets.ensure_plate_model()
    assert not path.exists()
