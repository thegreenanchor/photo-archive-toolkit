# Codex Mac App Prompt Playbook 🤖📸

Copy and paste these exact prompts directly into the **Codex Mac App** (or Codex CLI on macOS) to automate your photo archiving process.

---

## 🌟 1. The All-in-One Master Prompt (Recommended)

> Copy and paste this single prompt into Codex to have it guide and execute the entire workflow end-to-end:

```text
Read README.md and src/photo_archive.py first. I want to archive my photo libraries and external drive dumps to my connected external hard drive.

Please guide and assist me step-by-step:
1. Inspect this Mac: Find all Apple Photos libraries (`.photoslibrary`), Lightroom catalogs, local photo folders, and attached external drives.
2. Check storage: Show free space on my internal Mac drive and connected external drives to ensure we have enough storage.
3. Apple Photos Export: If I am archiving Apple Photos / iCloud Photos, help me verify that unmodified originals are being exported to an external staging folder (e.g. `/Volumes/<DriveName>/_photo-export-staging/<batch-name>`) and NOT to the internal Mac drive. Never scan `.photoslibrary` packages directly.
4. Install & Setup: Install the `photo-archive` CLI locally (`python3 -m pip install -e .`).
5. Scan: Run `photo-archive scan` with the appropriate `--source-class` (`icloud-export`, `lightroom-classic-originals`, `mac-local`, `external-backup-drive`) and `--batch-name` to generate a manifest and CSV.
6. Dedupe Audit: Run `photo-archive dedupe-report` to check for exact SHA-256 duplicate files across my sources.
7. Copy: Run `photo-archive copy` to copy files non-destructively into `<archive-root>/<category>/<batch-name>/` while preserving creation dates and `.xmp` / `.aae` sidecars.
8. Verify: Run `photo-archive verify` to validate 100% SHA-256 checksum match and output a verification report.

Safety Constraints:
- Never delete any source files or original photos.
- Preserve all timestamps and sidecars.
- Confirm target paths with me before running the copy step.
```

---

## 📋 2. Step-by-Step Individual Prompts

If you prefer to run the workflow phase-by-phase, use these individual prompts:

### Phase 1: Drive & System Inspection
```text
Read README.md. Please inspect my Mac to locate all photo sources:
1. List attached external drives (`/Volumes/`).
2. Search for Apple Photos libraries (`~/Pictures/*.photoslibrary`) and report their sizes and file counts.
3. Search for Lightroom catalogs (`*.lrcat`) or local photo folders.
4. Report available disk space on internal storage and all attached external volumes.
```

### Phase 2: Staging Apple Photos Exports
```text
I am getting ready to export unmodified originals from Apple Photos.
1. Help me select or create an export staging directory on my external hard drive (e.g. `/Volumes/<MyDrive>/_export_staging/2026-icloud-export`).
2. Give me clear instructions on how to use Apple Photos -> File -> Export -> Export Unmodified Original with IPTC as XMP enabled.
3. Once I finish exporting, check the exported folder to confirm file count and total size.
```

### Phase 3: Scanning & Building Manifest
```text
Now let's scan my photo sources using `photo-archive scan`.
1. Install `photo-archive` if not already installed (`python3 -m pip install -e .`).
2. Help me run `photo-archive scan` against my exported staging folder and any external drives.
3. Use proper `--source-class` tags (`icloud-export`, `mac-local`, `external-backup-drive`).
4. Output the manifest to `./manifests/scan.json` and CSV summary to `./manifests/scan.csv`.
5. Show me a summary of total files, total GB, and breakdown by file extension.
```

### Phase 4: Duplicate Analysis
```text
Let's analyze exact duplicates across my sources before copying.
1. Run `photo-archive dedupe-report --manifest ./manifests/scan.json --report-out ./manifests/duplicates.json`.
2. Tell me how many duplicate groups were found and how much potential storage space is duplicated.
```

### Phase 5: Archiving (`copy`)
```text
Let's execute the non-destructive copy to my archive drive.
1. Set the archive root to `/Volumes/<MyDrive>/Photo Archive`.
2. Run `photo-archive copy --manifest ./manifests/scan.json --archive-root "/Volumes/<MyDrive>/Photo Archive" --report-out ./manifests/copy-report.json`.
3. Confirm that all timestamps and sidecars (`.xmp`, `.aae`) were preserved and report the result.
```

### Phase 6: SHA-256 Verification
```text
Let's verify 100% file integrity of the archive.
1. Run `photo-archive verify --manifest ./manifests/scan.json --archive-root "/Volumes/<MyDrive>/Photo Archive" --report-out ./manifests/verify-report.json`.
2. Check for any missing files or hash mismatches and display a summary report.
```
