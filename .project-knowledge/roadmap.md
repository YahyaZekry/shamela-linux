# Roadmap

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14
> Forward-looking only. Check this before starting any task.

## Current Goal

Mount the user's existing Shamela Windows database (downloaded, previously worked on Windows) in the restored Linux build — figure out how the Linux app expects its data/library layout and how to feed it the Windows dataset.

**Research notes (start):**
- Shamela Windows data lives in a library/bookshelf layout: a root directory holding the app DB + `Books/` (`.bok` files + per-book `info.xml`/`index.xml`). The Linux build mirrors this via `Across.bin_directory` / `Across.os` routing in `shamela.py` and `dirs.py`.
- Need to confirm: what the user's database contains (DB file format, SQLite?), and which env var / config the Linux app uses to locate the library (`--library`, `SHAMELA_*`, `~/.shamela`, `~/Shamela`?). See `dirs.py`, `settings.py`, `dbmanager.py` in `decompiled/`.

---

## Known Bugs

- [ ] `uncompyle6` cannot decompile ~6+ construct patterns in this codebase (see `systems.md` for the list) — every one must be rebuilt by hand from `xdis`/`dis` output *(found: 2026-08-14)*
- [ ] App launch under the dev environment logs `qt.qpa.plugin: Could not find the Qt platform plugin "wayland"` + fontconfig/font warnings (`shamela-run.log`) — environment issue to solve before any "run from source" attempt *(found: 2026-08-14)*

---

## Active TODOs

- [ ] Future edits: work in the REPO copies (`/mnt/airfryer/Projects/Linux/shamela-linux/{d3,decompiled}`) rather than `/tmp/opencode`, so nothing is lost on reboot *(added: 2026-08-14)*
- [ ] DB mounting research (current goal): inspect the user's Windows Shamela database, map the Linux app's library/data lookup (`dirs.py`, `settings.py`, `dbmanager.py`, `shamela.py`), and document how to mount the Windows dataset in the Linux build *(added: 2026-08-14)*
- [ ] Run the failed-section fix pass over the remaining ~31 decompiled modules (only `customs`, `updater`, `options`, `shamela`, `displaybook`, `engine`, `ignore`, `searchboxes` are cleaned) — ongoing goal: finish the byte-exact source tree across all 39 modules *(added: 2026-08-14)*
- [ ] For each newly cleaned module: byte-verify every function, then `ast.parse` the whole file *(added: 2026-08-14)*
- [ ] Decide reconcile strategy: does `d3/` replace `decompiled/`, or should the cleaned files be copied back over the decompiled originals? *(added: 2026-08-14)*

---

## Planned Features

- [ ] Runtime restore: wire the byte-exact source into `dev-env/.venv` and launch the app from source instead of the frozen binary *(added: 2026-08-14)*
- [ ] Full-module bytecode equivalence audit (diff every function's `co_code` across all 39 modules) *(added: 2026-08-14)*
