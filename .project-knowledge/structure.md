# Project Structure

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-18
> All work artifacts are persisted in THIS repo. `/tmp/opencode` still holds copies but is no longer the only home.

## File Tree

```
/mnt/airfryer/Projects/Linux/shamela-linux/    # THIS REPO (persistent)
├── dev-env/.venv/                      # conda-style Python 3.7.12 env (xdis, uncompyle6)
├── shamela-extract/shamela_extracted/  # PyInstaller extraction (289 .pyc, PYZ-00.pyz)
│   ├── shamela.pyc                     # main entry code (level-1 CArchive)
│   └── PYZ-00.pyz_extracted/           # ~250 pyc: app modules + stdlib
├── decompiled/                         # uncompyle6 output, 39 app modules (decompiler baseline)
│   ├── shamela.py, across.py, engine.py, customs.py, mainwindow.py, ...
│   └── (dbmanager.py, downloader.py, exporter.py, quran.py, theme.py, ...)
├── d3/                                 # cleaned + byte-verified subset (8 modules)
│   ├── shamela.py, updater.py, options.py, customs.py
│   └── displaybook.py, engine.py, ignore.py, searchboxes.py
├── tools/                              # migration utilities
│   ├── migrate_full.py                 # full migration tool (map/catalog/convert phases)
│   ├── convert_poc.py                  # PoC single-book converter (predecessor)
│   └── data/
│       ├── golden_map.json             # title-match mapping (shamelaID -> modern book_id)
│       ├── gcat_map.json               # golden category -> modern category mapping
│       └── progress.db                 # resumability state (converted, catalog_done)
├── .git/
├── .project-knowledge/                 # this folder
└── README.md                           # repo overview
```

## Key Files

| File | Purpose |
|------|---------|
| `shamela.py` | Main entry; arch detection, platform init, launches the app window |
| `across.py` | `Across` — global runtime object (os, bin_directory, main_window, ...) referenced app-wide |
| `customs.py` | Shared Qt widgets/helpers (browsers, line edits, DPI, clipboard/attribution) |
| `engine.py` | Core application/engine logic (Lucene Index, Book, Importer classes) |
| `options.py` | Settings UI + `Settings` store (`_cache`, `COLOR_KEYS`, theme preview) |
| `updater.py` | Import/download queue, `prepareBar`/`prepareProgress` first-run bar |
| `displaybook.py` | Book display logic |
| `searchboxes.py` | Search UI boxes |
| `dbmanager.py` / `savebase.py` | SQLite persistence (not yet in d3) |
| `quran.py` / `quraninfo.py` | Quran content (not yet in d3) |
| `tools/migrate_full.py` | Full migration tool: map, catalog, convert phases |
| `tools/data/progress.db` | Resumability tracker for migration |
| `tools/data/golden_map.json` | Title-match mapping golden shamelaID to modern book_id |
| `tools/data/gcat_map.json` | Category mapping golden cats to modern cats |

## Migration Data Flow

```
Golden (source)                    Modern (target)
-----------                        ---------------
Books/<sid%10>/<sid>.mdb    -->    database/book/<id%1000>/<id>.db  (per-book SQLite metadata)
  book(id,part,page,nass)          database/store/page              (Lucene text)
  title(id,lvl,sub,tit)            database/store/title             (Lucene TOC)
  cp1256 encoding                  database/master.db               (catalog)
                                   UTF-8, normalized Arabic
```
