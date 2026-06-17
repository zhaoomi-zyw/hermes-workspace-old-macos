# HTML Preview Caching in Hermes WebUI

## Problem

The Hermes WebUI's built-in HTML preview (`MEDIA:/path/to/file.html`) caches rendered content by file path. After modifying an HTML file in-place, the preview continues showing the old version — even after hard-refresh and across sessions.

## Workaround

Save the modified HTML under a **new filename** (e.g., append `_v2`, `_v3`, `_v4`, or a timestamp) to bypass the cache:

```bash
cp /path/to/original.html /path/to/original_v2.html
```

Then link to the new filename with `MEDIA:/path/to/original_v2.html`.

This works because the cache key is the file path, not the file content or inode.

## When This Happens

- Editing HTML files in-place via `write_file` or `patch`
- Iterating on presentation decks, reports, or any HTML artifact
- The file content on disk is correct (verify with `grep`/`read_file`), but preview shows old version

## Verification

Always verify the on-disk content is correct before assuming it's a cache issue:
```bash
grep -c 'expected_text' /path/to/file.html
```
If the grep confirms the change but preview doesn't reflect it, use the new-filename workaround.
