#!/usr/bin/env python3
"""Copy prepared runtime song files to a local directory or rsync SSH target."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def bundle_file(bundle: Path, name: object) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError(f"{bundle.name}: expected a relative runtime filename")
    path = bundle / name
    if ".." in Path(name).parts or not path.resolve().is_relative_to(bundle.resolve()):
        raise ValueError(f"{bundle.name}: runtime path escapes bundle: {name}")
    return path


def runtime_files(source: Path) -> list[Path]:
    """Build an explicit manifest from metadata rather than copying source assets."""
    if not source.is_dir():
        raise ValueError(f"not a song directory: {source}")
    files: set[Path] = set()
    for bundle in sorted(source.iterdir()):
        if not bundle.is_dir() or bundle.name.startswith("."):
            continue
        metadata_path = bundle / "song.json"
        if not metadata_path.is_file():
            continue
        if bundle.is_symlink() or metadata_path.is_symlink():
            raise ValueError(f"{bundle.name}: song directories and metadata must not be symlinks")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError(f"{metadata_path}: expected a JSON object")
        files.add(metadata_path.relative_to(source))
        for key, extension in (("audio", ".wav"), ("chart", ".sm")):
            path = bundle_file(bundle, metadata.get(key))
            if not path.is_file() or path.suffix.lower() != extension:
                raise ValueError(f"{bundle.name}: {key} must reference an existing {extension} file: {path}")
            files.add(path.relative_to(source))
        cover = bundle_file(bundle, metadata.get("cover", "song.bmp"))
        if cover.exists():
            if not cover.is_file():
                raise ValueError(f"{bundle.name}: cover is not a file: {cover}")
            files.add(cover.relative_to(source))
        # Missing covers use the fallback image shipped with the game itself.
    if not files:
        raise ValueError("no prepared song bundles found")
    return sorted(files)


def sync_songs(source: Path, destination: str, dry_run: bool = False) -> int:
    source = source.expanduser().resolve()
    files = runtime_files(source)
    command = [
        "rsync", "-rtL", "--protect-args", "--itemize-changes",
        "--from0", "--files-from=-",
    ]
    if dry_run:
        command.append("--dry-run")
    # A trailing slash copies bundle directories into the destination, without
    # introducing an extra enclosing source directory. No deletion is requested.
    command.extend(["--", str(source) + "/", destination])
    manifest = b"".join(str(path).encode("utf-8") + b"\0" for path in files)
    print(f"{'Previewing' if dry_run else 'Syncing'} {len(files)} runtime files to {destination}", flush=True)
    return subprocess.run(command, input=manifest, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="local prepared song directory")
    parser.add_argument("destination", help="destination directory or user@host:/path/to/songs/")
    parser.add_argument("--dry-run", action="store_true", help="preview rsync changes without copying")
    args = parser.parse_args()
    if shutil.which("rsync") is None:
        parser.error("install rsync 3 or newer")
    try:
        return sync_songs(args.source, args.destination, args.dry_run)
    except (OSError, ValueError) as error:
        print(f"sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
