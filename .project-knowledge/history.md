# History

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14
> Past-only. Append-only — never delete entries.

## Removed

- ~~`--- This code section failed: ---` stubs~~ — replaced with real reconstructed source in `options.py`, `shamela.py`, `updater.py`, `customs.py` *(removed: 2026-08-14)*

---

## Fixed

- `detect_running_arch` (shamela.py) — decompiler choked on `JUMP_IF_TRUE_OR_POP` short-circuit; rebuilt as `normalize_arch(launched_arch()) or ('32' if sys.maxsize <= 4294967296 else '64')` → bytecode IDENTICAL *(fixed: 2026-08-14)*
- `prepareProgress` (updater.py) — `CALL_METHOD`/`COME_FROM` label clash; full 3-paragraph docstring + logic rebuilt from disassembly → bytecode IDENTICAL *(fixed: 2026-08-14)*
- `_settingsSnapshot` (options.py) — comprehension iterable was dropped (`for key in `); restored `self._previewKeys()` → bytecode IDENTICAL *(fixed: 2026-08-14)*
- `_changedPreviewKeys` (options.py) — same missing-iterable bug → bytecode IDENTICAL *(fixed: 2026-08-14)*
- `_buildHtmlFromParagraphs` (customs.py, ×2 occurrences) — decompiler emitted a broken 4-quote triple-quoted f-string (`f"""font-family:"{run['font']}"""`) that was a `SyntaxError`; consts (`'font-family:"'`, `'"'`) showed the original was `f'font-family:"{run["font"]}"'` → fixed *(fixed: 2026-08-14)*
- `realResolutions_new` (customs.py) — `SETUP_LOOP`/`SETUP_EXCEPT` label collision; per-monitor DPI function rebuilt from disassembly incl. docstring → bytecode IDENTICAL *(fixed: 2026-08-14)*
- `ReadersBrowser.keyPressEvent` (customs.py) — biggest failure; rebuilt from full disassembly incl. `wrapped=False` kwarg form (verified how 3.7 compiles `matchesShortcutEvent(event, 'Ctrl+Up', wrapped=False)`) and the `Qt.Key_F1 <= key <= Qt.Key_F35` chained comparison with its duplicated `Qt.Key_End` set member → bytecode IDENTICAL *(fixed: 2026-08-14)*
- `tools/migrate_full.py` catalog phase wrote the golden author **name** into `book.authors` (`'محمد رشيد رضا'`, `'-'`, or empty), but the app's `fillBookCache` expects comma-separated numeric author **ids** and crashes with `ValueError: invalid literal for int()`. Result: blank, unclickable rows for all 22,598 migrated books. Fixed: `authors = str(aid)` in the tool; live data backfilled to `main_author` *(fixed: 2026-08-19)*

---

## Decisions

- **Bytecode identity is the ground truth** — a reconstruction is only "done" when `co_code` matches the original; functional equivalence is not enough. *(2026-08-14)*
- **Persist artifacts in the repo** — all work products (d3/, decompiled/, shamela-extract/) were copied into the repo on 2026-08-14 so they survive reboots; /tmp/opencode is now just a scratch mirror. *(2026-08-14)*
- **Verify compiler behavior empirically** — before trusting a decompiler's guess about a construct, compile the candidate source with the real Py3.7 and compare bytecode (`dis.dis` probe). This is how `wrapped=False` was confirmed over the decompiler's `CALL_FUNCTION_KW` display. *(2026-08-14)*
- **Reproduce literals faithfully, even odd ones** — the duplicated `Qt.Key_End` inside the set literal in `keyPressEvent` is kept as-is (a set makes it harmless, and fidelity beats tidiness). *(2026-08-14)*
- **d3 is the clean working tree** — edits happen in `d3/`; `decompiled/` stays untouched as the decompiler baseline. *(2026-08-14)*
- **Migration uses InsertBook fast-path** — the converter uses `addDocument` after `Importer.deleteBooks` rather than the full `engine.Book.updatePage/updateTitle` flow (which requires a per-doc searcher lease). This is safe because the full run processes each book exactly once. Batched commits every 20 books keep the index consistent. *(2026-08-14)*
- **Resumability via progress.db** — the converter marks each golden_id as done in `tools/data/progress.db` only after a successful Lucene commit batch, so a crash loses at most one batch of work (20 books). No-pages books are marked done with count 0 (not retried). *(2026-08-14)*
- **In-place PYZ splicing is the patch delivery mechanism** — the installed binary gets a rebuilt PYZ (same module set + `shamela_patch`, `across` 12-byte-prefixed to call `install()` at first import) padded to the identical byte length and written over the PYZ region. Total exe size unchanged → bootloader cookie/TOC/`pydata`/ELF headers untouched. *(2026-08-19)*
- **sys.modules shims, not meta-path finders** — PyInstaller's `PyiFrozenImporter` is first in `meta_path` and answers every frozen name, so an appended finder never fires. Proxy shims pre-registered in `sys.modules` are consulted before any finder and trigger the real frozen import on `__getattr__`. *(2026-08-19)*
- **Everything in the patch must only log on failure** — `shamela_patch.py` is fully defensive; a patching error must degrade to the original behavior, never crash the app. *(2026-08-19)*
- **EXE_IN/EXE_OUT hardcoded in surgery.py** — reapply after reinstall = edit the two paths at the top (or keep the app at `~/Apps/shamela`), run one command, swap `shamela.new`. *(2026-08-19)*
