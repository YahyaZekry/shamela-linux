# Project Structure

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14
> The source archive and all work artifacts are now persisted in THIS repo. `/tmp/opencode` still holds copies and remains the active scratch area, but is no longer the only home.

## File Tree

```
/home/monst3r/Downloads/
└── shamela-linux-1448.2.tar.xz          # original distribution (167 MB)

/mnt/airfryer/Projects/Linux/shamela-linux/    # ← THIS REPO (persistent)
├── dev-env/.venv/                      # conda-style Python 3.7.12 env (xdis, uncompyle6)
├── shamela-extract/shamela_extracted/  # PyInstaller extraction (289 .pyc, PYZ-00.pyz + PYZ-00.pyz_extracted/)
│   ├── shamela.pyc                     # main entry code (level-1 CArchive)
│   └── PYZ-00.pyz_extracted/           # ~250 pyc: app modules + stdlib (109 top-level + subdirs: xml/, sqlite3/, userpaths/)
├── decompiled/                         # uncompyle6 output, 39 app modules (decompiler baseline)
│   ├── shamela.py, across.py, engine.py, customs.py, mainwindow.py, …
│   └── (dbmanager.py, downloader.py, exporter.py, quran.py, theme.py, …)
├── d3/                                 # cleaned + byte-verified subset (8 modules)
│   ├── shamela.py, updater.py, options.py, customs.py
│   └── displaybook.py, engine.py, ignore.py, searchboxes.py
├── .git/
└── .project-knowledge/                 # ← this folder

/tmp/opencode/                          # ← scratch copies of the above (EPHEMERAL, still used for work)
├── d3/, decompiled/, shamela-extract/  # same content as the repo copies
├── shamela-inspect/                    # early extraction/format inspection
├── reorg.sh                            # UNRELATED (book-folder reorg script)
├── shamela-run.log                     # app launch log (Qt/font warnings)
├── p4-004.png, p4o.txt, po1.txt, page-001.png  # OCR/screenshot scraps
```

## Key Files

| File | Purpose |
|------|---------|
| `shamela.py` | Main entry; arch detection, platform init, launches the app window |
| `across.py` | `Across` — global runtime object (os, bin_directory, main_window, …) referenced app-wide |
| `customs.py` | Shared Qt widgets/helpers (browsers, line edits, DPI, clipboard/attribution) |
| `engine.py` | Core application/engine logic |
| `options.py` | Settings UI + `Settings` store (`_cache`, `COLOR_KEYS`, theme preview) |
| `updater.py` | Import/download queue, `prepareBar`/`prepareProgress` first-run bar |
| `displaybook.py` | Book display logic |
| `searchboxes.py` | Search UI boxes |
| `dbmanager.py` / `savebase.py` | SQLite persistence (not yet in d3) |
| `quran.py` / `quraninfo.py` | Quran content (not yet in d3) |
