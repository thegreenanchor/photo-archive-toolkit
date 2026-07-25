"""
Photo Archive CLI - Non-destructive, checksum-verified photo library archiving.

Commands:
    scan          Scan source roots, detect sidecars, compute SHA-256, write manifest & CSV
    copy          Copy files from manifest to target archive using copy2 (preserves timestamps)
    verify        Verify destination files against manifest (presence, size, SHA-256 match)
    dedupe-report Group files by SHA-256 to report exact duplicates across batches
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Supported media extensions
MEDIA_EXTENSIONS: Set[str] = {
    # Images
    ".jpg", ".jpeg", ".heic", ".heif", ".png", ".tiff", ".tif",
    ".gif", ".bmp", ".webp",
    # RAWs
    ".arw", ".cr2", ".cr3", ".nef", ".orf", ".rw2", ".pef", ".dng", ".raf",
    # Videos
    ".mov", ".mp4", ".m4v", ".avi", ".mkv", ".3gp", ".wmv"
}

# Sidecar extensions
SIDECAR_EXTENSIONS: Set[str] = {".xmp", ".aae", ".json", ".xml"}

# Category folder mapping based on source class
SOURCE_CLASS_CATEGORY_MAP: Dict[str, str] = {
    "icloud-export": "01-icloud-photos",
    "lightroom-classic-originals": "02-lightroom-classic",
    "lightroom-classic-catalog-backup": "02-lightroom-classic",
    "lightroom-cloud-originals": "02-lightroom-cloud",
    "mac-local": "03-mac-local",
    "windows-local": "03-windows-local",
    "google-photos-backup": "03-google-photos",
    "external-backup-drive": "04-external-backup-drives",
}


def calculate_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_sidecars(media_path: Path) -> List[str]:
    """Find sidecar files (.xmp, .aae, .json) matching a media file stem."""
    sidecars = []
    parent = media_path.parent
    stem = media_path.stem.lower()

    if not parent.exists():
        return sidecars

    for item in parent.iterdir():
        if item.is_file() and not item.name.startswith("._"):
            if item.suffix.lower() in SIDECAR_EXTENSIONS:
                if item.stem.lower() == stem or item.name.lower().startswith(stem + "."):
                    sidecars.append(str(item.resolve()))
    return sorted(sidecars)


def scan_sources(
    source_configs: List[Tuple[Path, str, str]],
    exclude_dirs: Optional[List[str]] = None
) -> List[Dict]:
    """Scan source roots and build a manifest of media files."""
    exclude_dirs_set = set(exclude_dirs or [])
    records = []

    for source_root, source_class, batch_name in source_configs:
        source_root = source_root.resolve()
        if not source_root.exists():
            print(f"[WARN] Source root does not exist: {source_root}", file=sys.stderr)
            continue

        category = SOURCE_CLASS_CATEGORY_MAP.get(source_class, "04-external-backup-drives")

        for root, dirs, files in os.walk(source_root):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs_set and not d.startswith(".")]

            root_path = Path(root)

            for file_name in files:
                # Skip macOS/exFAT AppleDouble metadata files
                if file_name.startswith("._") or file_name.startswith(".DS_Store"):
                    continue

                file_path = root_path / file_name
                ext = file_path.suffix.lower()

                if ext not in MEDIA_EXTENSIONS:
                    continue

                try:
                    rel_path = file_path.relative_to(source_root)
                    stat = file_path.stat()
                    size_bytes = stat.st_size
                    mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    sha256_hash = calculate_sha256(file_path)
                    sidecars = find_sidecars(file_path)

                    target_rel_path = Path(category) / batch_name / rel_path

                    media_kind = "video" if ext in {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".3gp", ".wmv"} else "image"

                    record = {
                        "source_path": str(file_path.resolve()),
                        "source_root": str(source_root),
                        "source_class": source_class,
                        "batch_name": batch_name,
                        "category": category,
                        "relative_path": str(rel_path),
                        "archive_target_relative": str(target_rel_path),
                        "extension": ext,
                        "media_kind": media_kind,
                        "size_bytes": size_bytes,
                        "modified_at": mod_time,
                        "sha256": sha256_hash,
                        "sidecars": sidecars,
                    }
                    records.append(record)
                except Exception as e:
                    print(f"[ERROR] Failed scanning {file_path}: {e}", file=sys.stderr)

    return records


def cmd_scan(args):
    """Execute the scan command."""
    source_configs = []
    roots = args.source_root or []
    classes = args.source_class or []
    batches = args.batch_name or []

    if len(roots) != len(classes) or len(roots) != len(batches):
        print("[ERROR] Equal numbers of --source-root, --source-class, and --batch-name are required.", file=sys.stderr)
        sys.exit(1)

    for r, c, b in zip(roots, classes, batches):
        source_configs.append((Path(r), c, b))

    print(f"[*] Scanning {len(source_configs)} source root(s)...")
    records = scan_sources(source_configs, exclude_dirs=args.exclude_dir)

    manifest_data = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(records),
        "total_bytes": sum(r["size_bytes"] for r in records),
        "files": records,
    }

    manifest_path = Path(args.manifest_out).resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"[SUCCESS] Wrote manifest to: {manifest_path} ({len(records)} files, {manifest_data['total_bytes'] / (1024**3):.2f} GB)")

    if args.csv_out:
        csv_path = Path(args.csv_out).resolve()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        if records:
            fieldnames = list(records[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in records:
                    row = dict(r)
                    row["sidecars"] = ";".join(row["sidecars"])
                    writer.writerow(row)
            print(f"[SUCCESS] Wrote CSV summary to: {csv_path}")


def cmd_copy(args):
    """Execute the copy command (non-destructive, preserves metadata & sidecars)."""
    manifest_path = Path(args.manifest).resolve()
    archive_root = Path(args.archive_root).resolve()

    if not manifest_path.exists():
        print(f"[ERROR] Manifest file not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    files = manifest.get("files", [])
    print(f"[*] Copying {len(files)} files to archive root: {archive_root}")

    copied = 0
    skipped = 0
    errors = 0

    copy_results = []

    for item in files:
        src = Path(item["source_path"])
        dst = archive_root / item["archive_target_relative"]

        if not src.exists():
            print(f"[WARN] Source file missing: {src}", file=sys.stderr)
            errors += 1
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Check idempotency
        if dst.exists() and dst.stat().st_size == item["size_bytes"]:
            dst_hash = calculate_sha256(dst)
            if dst_hash == item["sha256"]:
                skipped += 1
                copy_results.append({"source": str(src), "target": str(dst), "status": "skipped"})
                continue

        try:
            shutil.copy2(src, dst)
            copied += 1

            # Copy associated sidecars
            for sidecar_str in item.get("sidecars", []):
                sidecar_src = Path(sidecar_str)
                if sidecar_src.exists():
                    sidecar_dst = dst.parent / sidecar_src.name
                    shutil.copy2(sidecar_src, sidecar_dst)

            copy_results.append({"source": str(src), "target": str(dst), "status": "copied"})
        except Exception as e:
            print(f"[ERROR] Failed copying {src} -> {dst}: {e}", file=sys.stderr)
            errors += 1

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_processed": len(files),
        "copied": copied,
        "skipped": skipped,
        "errors": errors,
        "details": copy_results,
    }

    if args.report_out:
        report_path = Path(args.report_out).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[SUCCESS] Wrote copy report to: {report_path}")

    print(f"[SUCCESS] Copy complete: {copied} copied, {skipped} skipped, {errors} errors.")


def cmd_verify(args):
    """Execute the verify command."""
    manifest_path = Path(args.manifest).resolve()
    archive_root = Path(args.archive_root).resolve()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    files = manifest.get("files", [])
    print(f"[*] Verifying {len(files)} files in archive: {archive_root}")

    verified = 0
    missing = 0
    mismatched = 0

    results = []

    for item in files:
        dst = archive_root / item["archive_target_relative"]
        status = "ok"

        if not dst.exists():
            missing += 1
            status = "missing"
        elif dst.stat().st_size != item["size_bytes"]:
            mismatched += 1
            status = "size_mismatch"
        else:
            actual_hash = calculate_sha256(dst)
            if actual_hash != item["sha256"]:
                mismatched += 1
                status = "hash_mismatch"
            else:
                verified += 1

        results.append({
            "target": str(dst),
            "expected_hash": item["sha256"],
            "status": status,
        })

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "expected_total": len(files),
        "verified": verified,
        "missing": missing,
        "mismatched": mismatched,
        "details": results,
    }

    if args.report_out:
        report_path = Path(args.report_out).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[SUCCESS] Wrote verification report to: {report_path}")

    print(f"[RESULTS] Verified: {verified}/{len(files)} | Missing: {missing} | Mismatched: {mismatched}")


def cmd_dedupe_report(args):
    """Execute duplicate analysis command."""
    manifest_path = Path(args.manifest).resolve()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    files = manifest.get("files", [])
    print(f"[*] Analyzing duplicates among {len(files)} files...")

    hash_groups: Dict[str, List[Dict]] = {}
    for f in files:
        h = f["sha256"]
        hash_groups.setdefault(h, []).append(f)

    duplicate_groups = {h: group for h, group in hash_groups.items() if len(group) > 1}

    total_dup_files = sum(len(g) for g in duplicate_groups.values())
    wasted_bytes = sum((len(g) - 1) * g[0]["size_bytes"] for g in duplicate_groups.values())

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duplicate_groups_count": len(duplicate_groups),
        "total_duplicate_files": total_dup_files,
        "wasted_bytes": wasted_bytes,
        "duplicate_groups": list(duplicate_groups.values()),
    }

    report_path = Path(args.report_out).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[SUCCESS] Duplicate report: {len(duplicate_groups)} duplicate groups ({total_dup_files} files, {wasted_bytes / (1024**2):.2f} MB potential savings).")
    print(f"[SUCCESS] Wrote duplicate report to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Photo Archive CLI - Checksum-verified photo archiving.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scan subcommand
    scan_parser = subparsers.add_parser("scan", help="Scan source directories for media files.")
    scan_parser.add_argument("--source-root", action="append", required=True, help="Path to source directory (can be specified multiple times).")
    scan_parser.add_argument("--source-class", action="append", required=True, choices=list(SOURCE_CLASS_CATEGORY_MAP.keys()), help="Class of source (icloud-export, mac-local, etc.).")
    scan_parser.add_argument("--batch-name", action="append", required=True, help="Name for this batch (e.g. 2026-07-25-icloud-photos).")
    scan_parser.add_argument("--manifest-out", required=True, help="Path for output JSON manifest.")
    scan_parser.add_argument("--csv-out", help="Optional path for output CSV summary.")
    scan_parser.add_argument("--exclude-dir", action="append", help="Exclude directory name.")
    scan_parser.set_defaults(func=cmd_scan)

    # Copy subcommand
    copy_parser = subparsers.add_parser("copy", help="Copy files from manifest to archive root.")
    copy_parser.add_argument("--manifest", required=True, help="Path to input JSON manifest.")
    copy_parser.add_argument("--archive-root", required=True, help="Target archive root directory.")
    copy_parser.add_argument("--report-out", help="Optional path for JSON copy report.")
    copy_parser.set_defaults(func=cmd_copy)

    # Verify subcommand
    verify_parser = subparsers.add_parser("verify", help="Verify archive integrity against manifest.")
    verify_parser.add_argument("--manifest", required=True, help="Path to input JSON manifest.")
    verify_parser.add_argument("--archive-root", required=True, help="Target archive root directory.")
    verify_parser.add_argument("--report-out", help="Optional path for JSON verification report.")
    verify_parser.set_defaults(func=cmd_verify)

    # Dedupe report subcommand
    dedupe_parser = subparsers.add_parser("dedupe-report", help="Report duplicate files in manifest.")
    dedupe_parser.add_argument("--manifest", required=True, help="Path to input JSON manifest.")
    dedupe_parser.add_argument("--report-out", required=True, help="Path for JSON duplicate report.")
    dedupe_parser.set_defaults(func=cmd_dedupe_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
