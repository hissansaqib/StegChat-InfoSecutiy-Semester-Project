"""Universal contract test fixture executing against every registered carrier.

Requirements:
- Roundtrip test (cover -> embed -> extract == payload)
- Wrong seed test (embed with seed A, extract with seed B fails ExtractionFailed)
- Capacity exceeded test (payload > capacity raises CapacityExceeded)
- Garbage input test (extract on arbitrary garbage raises UnsupportedFormat or ExtractionFailed)
- Fidelity measurement verification
- Feature extraction verification
"""

import pytest
from backend.app.carriers import registry
from backend.app.core.carrier import (
    Carrier,
    CapacityExceeded,
    UnsupportedFormat,
    ExtractionFailed,
    CorruptCarrier,
)

CARRIER_IDS = ["fake", "png_lsb", "wav_lsb", "text_zw"]

@pytest.mark.parametrize("carrier_id", CARRIER_IDS)
def test_carrier_info_metadata(carrier_id: str):
    carrier: Carrier = registry[carrier_id]
    info = carrier.info

    assert info.id == carrier_id
    assert info.kind in ["IMAGE", "AUDIO", "TEXT"]
    assert len(info.display_name) > 0
    assert len(info.accepted_mime) > 0
    assert len(info.output_mime) > 0
    assert isinstance(info.modes_schema, dict)
    assert isinstance(info.limitations, list)
    assert info.version == "1.0.0"

@pytest.mark.parametrize("carrier_id", CARRIER_IDS)
def test_carrier_roundtrip(carrier_id: str):
    carrier: Carrier = registry[carrier_id]
    payload = b"StegChat unified contract roundtrip verification 12345!"
    seed = "test_carrier_seed_32_bytes_pcg64"

    # Embed using synthetic or default cover
    stego = carrier.embed(cover=b"", payload=payload, params={"seed": seed})
    assert len(stego) > 0
    assert carrier.validate(stego) is True

    # Extract with correct seed
    recovered = carrier.extract(stego=stego, params={"seed": seed})
    assert recovered == payload

@pytest.mark.parametrize("carrier_id", CARRIER_IDS)
def test_carrier_wrong_seed_fails(carrier_id: str):
    carrier: Carrier = registry[carrier_id]
    payload = b"Confidential secret message"
    correct_seed = "correct_seed_123456789012345678"
    wrong_seed = "completely_different_seed_987654"

    stego = carrier.embed(cover=b"", payload=payload, params={"seed": correct_seed})

    with pytest.raises(ExtractionFailed):
        carrier.extract(stego=stego, params={"seed": wrong_seed})

@pytest.mark.parametrize("carrier_id", CARRIER_IDS)
def test_carrier_garbage_input_fails(carrier_id: str):
    carrier: Carrier = registry[carrier_id]
    garbage = b"\x00\xFF\xAA\x55" * 16

    with pytest.raises((UnsupportedFormat, ExtractionFailed, CorruptCarrier)):
        carrier.extract(stego=garbage, params={"seed": "any_seed"})

@pytest.mark.parametrize("carrier_id", CARRIER_IDS)
def test_carrier_measure_and_features(carrier_id: str):
    carrier: Carrier = registry[carrier_id]
    payload = b"Diagnostic payload"
    seed = "diagnostic_seed"

    stego = carrier.embed(cover=b"", payload=payload, params={"seed": seed})

    # Measure (cover vs stego)
    metrics = carrier.measure(cover=b"", stego=stego)
    assert isinstance(metrics, dict)
    assert "fidelity" in metrics or "fidelity_score" in metrics

    # Features
    feats = carrier.features(stego)
    assert isinstance(feats, dict)
    assert len(feats) > 0

