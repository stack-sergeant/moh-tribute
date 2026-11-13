"""Refresh the Army citation-index snapshots.

The live army.mil pages sometimes refuse scripted clients. This downloader
asks the Internet Archive for the newest successful capture of each page and
saves the original HTML under data/raw/army/. The pages are U.S. government
works.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "army"
UA = "ValorRecordDataPipeline/1.0 (educational archive of public-domain citations)"


def latest_capture(filename: str) -> str:
    url = (
        "https://web.archive.org/cdx/search/cdx?url=www.army.mil/medalofhonor/"
        f"{filename}&output=json&fl=timestamp,statuscode&filter=statuscode:200&limit=-1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        rows = json.loads(response.read().decode())
    data = rows[1:] if rows and rows[0][0] == "timestamp" else rows
    if not data:
        raise RuntimeError(f"no capture for {filename}")
    return data[-1][0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for number in range(1, 33):
        filename = f"citations{number}.html"
        timestamp = latest_capture(filename)
        source = f"https://www.army.mil/medalofhonor/{filename}"
        wayback = f"https://web.archive.org/web/{timestamp}id_/{source}"
        dest = OUT / filename
        print(filename, timestamp, flush=True)
        urllib.request.urlretrieve(wayback, dest)
        raw = dest.read_bytes()
        if raw[:2] == b"\x1f\x8b":
            import gzip

            dest.write_bytes(gzip.decompress(raw))
        manifest[filename] = {"timestamp": timestamp, "source": source, "wayback": wayback}
        time.sleep(0.4)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
