# Systems

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14

This is a reverse-engineering project, so "systems" = the pipeline stages rather than app subsystems. (The app itself is a Qt desktop app with SQLite persistence, but we don't build it — we restore its source.)

## Restoration Pipeline

| Stage | Status | Details |
|-------|--------|---------|
| Extraction | ✅ Done | `shamela-extract/` — pulled main entry from CArchive, extracted `PYZ-00.pyz` into ~250 `.pyc` files |
| Decompilation | 🟡 Partial | uncompyle6 over 39 app modules → `decompiled/`; 6+ functions failed decompilation and needed manual reconstruction |
| Byte-exact verification | 🟡 Partial | `co_code` identity check implemented; 6 reconstructed functions + 2 f-string fixes verified IDENTICAL. Only 8 of 39 modules are in the cleaned `d3/` tree |
| Manual reconstruction | 🟡 Ongoing | Full-disassembly rebuild where uncompyle6 emits `--- This code section failed: ---` stubs |
| Runtime restore (run from source) | 🔴 Not started | Long-term goal; venv is ready but no source run attempted yet |

## Known Decompiler Failure Modes (why manual work is needed)

- `JUMP_IF_TRUE_OR_POP` chains (`a() or b` short-circuit) — shamela.py `detect_running_arch`
- `CALL_METHOD` + `COME_FROM` label clashes — updater.py `prepareProgress`
- `CALL_FUNCTION_KW` with kwarg-name tuple on stack — customs.py `keyPressEvent` (`wrapped=False`)
- Empty comprehension iterable (`for key in `) — options.py `_settingsSnapshot`/`_changedPreviewKeys`
- Triple-quoted f-strings with an inner `"` — customs.py `_buildHtmlFromParagraphs` (decompiler emitted a 4-quote `"""` bug)
- Mixed `SETUP_LOOP`/`SETUP_EXCEPT` + label collisions — customs.py `realResolutions_new`
