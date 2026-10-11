"""Download the pre-trained CropGuard disease model for AI Crop Disease Identification.

Run from the ``backend`` directory:

    python scripts/download_disease_model.py

It fetches two files into ``models/plant_disease`` (override with ``--dir``):

- ``classes.json``      - the ordered class list (small, also committed),
- ``cropguard.onnx``    - the ResNet50 classifier (~92 MB, not committed).

Source: https://huggingface.co/XiElonMAsk/cropguard-models (CC-BY-SA-4.0),
a ResNet50 fine-tuned on the PlantVillage dataset (Mohanty, Hughes & Salathe,
2016). The model file is intentionally not stored in git because of its size.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

REPO = "XiElonMAsk/cropguard-models"
BASE_URL = f"https://huggingface.co/{REPO}/resolve/main"
FILES = ("classes.json", "cropguard.onnx")
MIN_EXPECTED_BYTES = {"cropguard.onnx": 80_000_000}

DEFAULT_DIR = Path(__file__).resolve().parents[1] / "models" / "plant_disease"


def _download(url: str, target: Path) -> None:
    print(f"  downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "ANNADATA/1.0"})
    with urllib.request.urlopen(request) as response, target.open("wb") as handle:
        while chunk := response.read(1024 * 256):
            handle.write(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="destination directory")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = parser.parse_args()

    args.dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = args.dir / name
        if target.exists() and not args.force:
            print(f"  {name} already present ({target.stat().st_size} bytes), skipping")
            continue
        _download(f"{BASE_URL}/{name}", target)
        size = target.stat().st_size
        minimum = MIN_EXPECTED_BYTES.get(name)
        if minimum is not None and size < minimum:
            print(f"  ERROR: {name} is only {size} bytes; download looks incomplete.", file=sys.stderr)
            return 1
        print(f"  saved {name} ({size:,} bytes)")

    print(f"\nDone. Model files are in {args.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
