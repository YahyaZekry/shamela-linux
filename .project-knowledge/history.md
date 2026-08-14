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
- Artifact-loss risk — `d3/`, `decompiled/`, and `shamela-extract/` (289 pyc) copied from `/tmp/opencode` into the repo; verified copy integrity (d3 parses, subdirs intact). Was a Roadmap Known Bug → resolved. *(fixed: 2026-08-14)*

---

## Decisions

- **Bytecode identity is the ground truth** — a reconstruction is only "done" when `co_code` matches the original; functional equivalence is not enough. *(2026-08-14)*
- **Persist artifacts in the repo** — all work products (d3/, decompiled/, shamela-extract/) were copied into the repo on 2026-08-14 so they survive reboots; /tmp/opencode is now just a scratch mirror. *(2026-08-14)*
- **Verify compiler behavior empirically** — before trusting a decompiler's guess about a construct, compile the candidate source with the real Py3.7 and compare bytecode (`dis.dis` probe). This is how `wrapped=False` was confirmed over the decompiler's `CALL_FUNCTION_KW` display. *(2026-08-14)*
- **Reproduce literals faithfully, even odd ones** — the duplicated `Qt.Key_End` inside the set literal in `keyPressEvent` is kept as-is (a set makes it harmless, and fidelity beats tidiness). *(2026-08-14)*
- **d3 is the clean working tree** — edits happen in `d3/`; `decompiled/` stays untouched as the decompiler baseline. *(2026-08-14)*
