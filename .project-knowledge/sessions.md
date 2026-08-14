# Session Log

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14
> Append-only — never edit past entries.

| Date | Summary |
|------|---------|
| 2026-08-14 | Extracted the PyInstaller-frozen Shamela Linux 1448.2 binary (main `shamela.pyc` + `PYZ-00.pyz` → ~250 pyc), decompiled all 39 app modules with uncompyle6 into `/tmp/opencode/decompiled/`. |
| 2026-08-14 | Created `/tmp/opencode/d3/` — cleaned working tree for the first 8 modules (shamela, updater, options, customs, displaybook, engine, ignore, searchboxes). |
| 2026-08-14 | Fixed all 6 `--- This code section failed: ---` decompilation failures + 2 broken f-strings in `d3/`: `detect_running_arch`, `prepareProgress`, `_settingsSnapshot`, `_changedPreviewKeys`, `realResolutions_new`, `ReadersBrowser.keyPressEvent`, `_buildHtmlFromParagraphs` (×2). All verified byte-identical to the original `.pyc` via `co_code` comparison; whole tree parses clean; zero failure markers remain. |
| 2026-08-14 | Persisted work artifacts into the repo (see history): copied `d3/`, `decompiled/` (39 modules), and `shamela-extract/` (289 pyc) from `/tmp/opencode`, verified integrity. Created `.project-knowledge/`. |
| 2026-08-14 | New goal set: mount the user's Windows Shamela database in the Linux build. Initial research notes added to roadmap. Repo committed + pushed. |
