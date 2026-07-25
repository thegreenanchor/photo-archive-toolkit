# Codex CLI Mac Prompt

Copy and paste the exact prompt below into Codex CLI on your Mac to have Codex guide you through scanning, copying, and verifying your photo library onto your external hard drive.

---

```text
Read README.md first. I want to archive my photo library and external drives to my connected external hard drive using the photo-archive CLI tool.

Please help me step-by-step:
1. Inspect this Mac to locate Apple Photos libraries, Lightroom catalogs, and attached external drives.
2. Check internal and external disk space to make sure we don't run out of storage.
3. Help me export unmodified originals from Apple Photos to an export staging folder on my external drive if needed.
4. Help me run `photo-archive scan` with the proper `--source-class` and `--batch-name` flags.
5. Review the generated JSON manifest and duplicate report before taking action.
6. Execute `photo-archive copy` to non-destructively copy files to the archive root.
7. Run `photo-archive verify` to guarantee 100% SHA-256 checksum verification.

Follow all safety rules:
- Never delete source files.
- Never scan .photoslibrary packages directly.
- Preserve all timestamps and .xmp / .aae sidecar files.
```
