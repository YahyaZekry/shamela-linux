# Shamela Linux

Reverse-engineered source code and migration tools for the [Shamela Library](https://shamela.ws/) Islamic library app (Linux/AppImage).

## What is this?

The Shamela app at `~/Apps/shamela/` is a **Python 3.7.12** desktop application (PyInstaller-frozen, Qt widgets, Lucene search) that was originally a Windows-only product. This repo contains:

1. **Decompiled and cleaned Python source** — recovered from the frozen `.pyc` bytecode
2. **Migration tools** — to import the legacy "Golden Shamela" library (29,278 books in `.mdb` Access format) into the modern Linux app

## Directory Structure

| Directory | Contents |
|-----------|----------|
| `d3/` | Clean decompiled Python source (the 8 core modules, byte-verified) |
| `decompiled/` | Full decompiled Python source (all 39 app modules, ~30k lines) |
| `tools/` | Migration utilities (`migrate_full.py`, `convert_poc.py`) |
| `tools/data/` | Migration artifacts (title mappings, category mappings, progress tracker) |
| `dev-env/` | Python 3.7.12 virtualenv (matches the app's bundled Python) |
| `shamela-extract/` | PyInstaller extraction output |

## Migration: Golden Shamela to Modern App

The primary tool is `tools/migrate_full.py`, which migrates the legacy Windows Shamela 3.x library into the modern Linux app.

### What it does

- **Title-matches** 6,678 golden books to existing modern catalog entries (22.8%)
- **Adds 22,593 new books** (with authors and categories) to the modern catalog
- **Converts all 29,276 books**: reads `.mdb` files, normalizes Arabic text, creates per-book SQLite databases, and indexes everything into Lucene
- Result: **29,276 of 29,278** golden books are now in the modern app (2 had zero pages)

### How to run

```bash
source dev-env/.venv/bin/activate

# Run the full migration (map + catalog + convert):
python tools/migrate_full.py all

# Or run phases individually:
python tools/migrate_full.py map      # title-match golden to modern
python tools/migrate_full.py catalog  # add unmatched books to master.db
python tools/migrate_full.py convert  # convert .mdb files to SQLite + Lucene

# Force re-convert on-disk books (default: skip them):
python tools/migrate_full.py convert --force-ondisk

# Commit Lucene indexes every N books (default: 20):
python tools/migrate_full.py convert --commit-every 50
```

**Important**: Close the Shamela app before running the migration (no SQLite/Lucene contention).

The tool is **resumable** — if it crashes, re-running the same command picks up where it left off (progress tracked in `tools/data/progress.db`).

## Tech Stack

| Component | Details |
|-----------|---------|
| App version | Shamela Library Linux 1448.2 |
| Python | 3.7.12 (CPython, x86_64) |
| Framework | PyQt / Qt widgets |
| Search engine | Lucene 10.4 (via JPype1) |
| Database | SQLite (catalog) + per-book SQLite (metadata) + Lucene (text) |
| Arabic text | cp1256 (golden) -> UTF-8 with AlKhalil normalization |
| Decompiler | uncompyle6 3.9.0, xdis 6.0.5 |

## Key Commands

```bash
# Activate the app-matching virtualenv
source dev-env/.venv/bin/activate

# Run migration
python tools/migrate_full.py all

# Check migration progress
sqlite3 tools/data/progress.db "SELECT count(*) FROM converted;"

# Verify a specific book in the modern database
sqlite3 ~/Apps/shamela/database/master.db "SELECT id, title FROM book WHERE id = 499;"
```

## Current Status

**Migration: COMPLETE** — All 29,276 books have been converted and are in the modern app.

**Post-migration work remaining:**
- [ ] Set author alpha sort values for ~22k new books
- [ ] Populate bibliography/search stores for book/author search
- [ ] Verify everything in the live app UI
- [ ] Continue cleaning decompiled source (8/39 modules done)

## Notes

- The app's JRE is at `app/linux/64/jre/2`, Lucene JARs at `app/lucene/2`
- The original `.mdb` files live at `Books/<shamelaID%10>/<shamelaID>.mdb` — keyed by the golden `shamelaID`, not by golden `id`
- The golden `id`, golden `shamelaID`, and modern `book_id` are three different numbering schemes — title matching is the only way to map between them
- Backups: `master.db.bak` is created before each migration run
