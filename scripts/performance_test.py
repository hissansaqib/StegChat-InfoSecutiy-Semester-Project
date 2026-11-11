"""Performance test for embed/extract operations.

Runs on the local machine and records the raw timings (no extrapolation).
The results are appended to ``docs/benchmark-results.md`` together with
machine details (CPU, OS, Python version).

Supported sizes:
* PNG images: 1 MP, 5 MP, 10 MP (RGB, no alpha)
* WAV audio: 10 s and 60 s (16‑bit PCM, 44.1 kHz, mono)

The script uses the carrier registry, therefore it works with any
registered carrier that supports the given media type.
"""

import io
import json
import platform
import time
from pathlib import Path

import numpy as np
from PIL import Image
import wave

from backend.app.carriers import list_carriers, get_carrier

# ---------------------------------------------------------------------------
# Helpers to generate synthetic covers
# ---------------------------------------------------------------------------

def generate_png(width: int, height: int) -> bytes:
    """Create a random RGB PNG of the requested dimensions."""
    arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_wav(duration_sec: int, sample_rate: int = 44100) -> bytes:
    """Generate a 16‑bit PCM wave file consisting of a sine tone.

    ``duration_sec`` is the length in seconds.
    """
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    freq = 440  # A4 tone
    signal = (0.5 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(signal.tobytes())
    return buf.getvalue()

# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def benchmark_carrier(carrier_id: str, media_type: str, cover_bytes: bytes, payload_bytes: int) -> dict:
    """Measure embed and extract time for a single carrier.

    Returns a dict with ``embed_ms`` and ``extract_ms``.
    """
    carrier_cls = get_carrier(carrier_id)
    carrier = carrier_cls()
    # Generate a random payload of the requested size
    payload = np.random.randint(0, 256, payload_bytes, dtype=np.uint8).tobytes()

    # Embed
    start = time.perf_counter()
    stego = carrier.embed(cover_bytes, payload)  # type: ignore[arg-type]
    embed_ms = (time.perf_counter() - start) * 1000

    # Extract
    start = time.perf_counter()
    extracted = carrier.extract(stego)  # type: ignore[arg-type]
    extract_ms = (time.perf_counter() - start) * 1000

    return {
        "carrier_id": carrier_id,
        "media_type": media_type,
        "payload_bytes": payload_bytes,
        "embed_ms": embed_ms,
        "extract_ms": extract_ms,
    }

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    results = []
    # Choose carriers that support each media type
    carriers = list_carriers()
    for carrier_id in carriers:
        carrier_cls = get_carrier(carrier_id)
        carrier = carrier_cls()
        # Detect supported kind via carrier.info (assumed to have 'kind')
        kind = getattr(carrier, "info", {}).get("kind", "UNKNOWN")
        if kind == "IMAGE":
            for megapixels in (1, 5, 10):
                side = int((megapixels * 1_000_000) ** 0.5)
                cover = generate_png(side, side)
                # Payload size: 10 % of carrier capacity (or 1 KB minimum)
                capacity = carrier.capacity(cover)
                payload = max(1024, int(0.1 * capacity))
                results.append(benchmark_carrier(carrier_id, "IMAGE", cover, payload))
        elif kind == "AUDIO":
            for duration in (10, 60):
                cover = generate_wav(duration)
                capacity = carrier.capacity(cover)
                payload = max(1024, int(0.1 * capacity))
                results.append(benchmark_carrier(carrier_id, "AUDIO", cover, payload))
        else:
            continue

    # Append results to docs/benchmark-results.md
    md_path = Path(__file__).parents[1] / "docs" / "benchmark-results.md"
    machine = platform.uname()
    header = f"\n## Performance benchmark – {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += f"*OS*: {machine.system} {machine.release}\n"
    header += f"*Machine*: {machine.node}\n"
    header += f"*Processor*: {machine.processor}\n"
    header += f"*Python*: {platform.python_version()}\n\n"
    table = "| Carrier | Media | Payload (bytes) | Embed (ms) | Extract (ms) |\n"
    table += "|--------|-------|----------------|-----------|--------------|\n"
    for r in results:
        table += f"| {r['carrier_id']} | {r['media_type']} | {r['payload_bytes']} | {r['embed_ms']:.2f} | {r['extract_ms']:.2f} |\n"
    md_path.write_text(md_path.read_text(encoding="utf-8") + header + table)
    print("Benchmark results appended to", md_path)

if __name__ == "__main__":
    main()

