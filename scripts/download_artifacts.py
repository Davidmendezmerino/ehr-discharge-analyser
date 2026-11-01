"""Download the pinned EHR runtime artifacts without additional dependencies."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def valid(path, item):
    if not path.is_file() or path.stat().st_size != item["size"]:
        return False
    if "sha256" in item:
        digest = hashlib.sha256()
    else:
        digest = hashlib.sha1()
        digest.update(f"blob {item['size']}\0".encode("ascii"))
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    expected = item.get("sha256", item.get("git_blob_sha1"))
    return digest.hexdigest() == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--small-only", action="store_true", help="Verify setup using files smaller than 1 MiB")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "artifacts.manifest.json").read_text(encoding="utf-8"))
    base = f"https://huggingface.co/spaces/{manifest['space']}/resolve/{manifest['revision']}/"
    selected = [item for item in manifest["files"] if not args.small_only or item["size"] < 1024 * 1024]
    for item in selected:
        relative = item["path"]
        destination = (ROOT / relative).resolve()
        if not destination.is_relative_to(ROOT):
            raise ValueError(f"Path leaves repository: {relative}")
        if destination.exists():
            if valid(destination, item):
                print(f"Verified existing: {relative}")
                continue
            raise ValueError(f"Existing file differs; preserved: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(base + relative, headers={"User-Agent": "EHR-assets/1.0"})
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".part", delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(request, timeout=180) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        if not valid(temporary, item):
            raise ValueError(f"Integrity check failed; partial preserved at {temporary}")
        temporary.replace(destination)
        print(f"Downloaded and verified: {relative}")
    print(f"Verified {len(selected)} runtime artifacts.")
    if args.small_only:
        print("Setup check only: run again without --small-only before starting inference.")


if __name__ == "__main__":
    main()
