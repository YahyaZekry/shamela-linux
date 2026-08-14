# Features & Workflows

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14

## Project Deliverables

- **[decompiled/ — full module set]** — uncompyle6 output for all 39 app modules (original, unmodified decompiler output) *(built: 2026-08-14)*
- **[d3/ — byte-exact source tree]** — the cleaned, verified subset; goal is to grow this to cover all 39 modules with every function byte-identical to the original `.pyc` *(active)*

## App Feature Surface (learned so far from the source)

- **Book library** — browse/search books (searchboxes.py, bookslist.py), favorites tree (favoritetree.py)
- **Book display** — QTextBrowser-based reader with NVDA screen-reader support (customs.py `ReadersBrowser`), RTL/LTR handling, per-baseline fonts (font_pages, font_matn, font_footnotes, …)
- **Copy/attribution pipeline** — `BrowserMixin`: plain-text extraction → clean HTML rebuild → attribution; Quran vs Book are mutually exclusive content types; honorifics decomposed, Arabic-Indic digits → ASCII
- **First-run import bar** — updater.py `prepareBar`/`prepareProgress`: each queued book owns 1/100th of the bar, high-water mark holds position during long steps
- **Settings & theme** — options.py: `Settings` store with `_cache`, preview snapshot/restore over `_previewKeys()`, dark-variant color keys
- **DPI handling** — per-monitor DPI via `shcore.GetDpiForMonitor` with legacy `GetDeviceCaps` fallback, then 96 (customs.py `realResolutions_new`/`realResolutions_old`, `windowsDpiDots`, `scaling`)
- **Quran module** — quran.py/quraninfo.py (not yet in d3), SQLite-backed (dbmanager.py/savebase.py)

## Verification Workflow (per reconstructed function)

1. `load_module()` original `.pyc` → locate code object by `co_name`
2. `compile()` reconstructed source → same lookup
3. Compare `co_code` → must be byte-identical
4. Syntax-check all `.py` in the tree with `ast.parse`
5. `grep` for `code section failed` / `Parse error` markers → must be empty
