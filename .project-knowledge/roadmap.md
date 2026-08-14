# Roadmap

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14
> Forward-looking only. Check this before starting any task.

## Current Goal

Migrate the user's golden shamela (legacy Windows Shamela 3.x library, 29,278 books) into the modern Linux Shamela app — not a mount: formats are structurally incompatible.

**Status: PoC proven (2026-08-14).** `tools/convert_poc.py` converts golden `.mdb` → modern per-book SQLite + Lucene `store/` + `master.db` marking; 3 books live in the app (499, 13682, 9486). Full detail in `sessions.md`.

**Architecture facts (validated):**
- Golden (source): `Books/<id%10>/<id>.mdb` — Jet/Access, `book(id,part,page,nass)` + `title(id,lvl,sub,tit)`, text **cp1256** (access_parser returns latin1-mojibake str → re-encode `latin1`→`cp1256`). Catalog: `book_index.db` `books` table.
- Modern (target): `database/master.db` catalog; `database/book/<id%1000:03d>/<id>.db` (`page(id,part,page,number,services)` + `title(id,page,parent)`); **page/title text lives in Lucene `database/store/{page,title}`** — per-book SQLite has no text. Doc id `"{book_id}-{page_id}"`; fields `body`(TEXT), `m_body`/`n_body`(ANALYSE); `Book._getDoc` adds ORD sorters from `CoreDb.sorter(book_id)`.
- **ID spaces differ:** golden `shamelaID` ≠ modern `book_id`. Map by title match. Golden-only books (~24k) need new catalog rows in `master.db` (fields/fieldsBooks join → author/category).
- Runtime: `d3/` first in `sys.path` (clean decompile), `decompiled/` fallback; stub `dbmanager` with `CoreDb.sorter`; boot = `Across.home_directory` + `Across.lucene_version=2` + `jpype.startJVM(classpath=["<home>/app/lucene/2/*"])` + bundled JRE.
- Title quirks: golden `title` table can repeat ids → renumber + remap parents. `title.page` derived by startswith-match (works well). `part` column: `''` single-part, else `str(part)`.

**Open items (next):**
- [ ] Full converter run over all 29k golden books (title-match map + add catalog rows for absent books).
- [ ] Confirm update machinery won't re-download/overwrite converted books (`major_online` vs `major_ondisk` checks look safe).
- [ ] Verify in the live app UI (books appear under downloaded; open + navigate + TOC + part combo).

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
