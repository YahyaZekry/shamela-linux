# Roadmap

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-18
> Forward-looking only. Check this before starting any task.

## Current Goal

**Migration COMPLETE + runtime patch SHIPPED.** `tools/migrate_full.py` finished: 29,276/29,278 golden books converted (2 had zero pages, skipped); catalog added 22,593 new book/author/category rows. Patch (background image, books-tab prefill, timing) is LIVE in the installed binary at `~/Apps/shamela/app/linux/64/bin/shamela` (tooling in `patch/`).

**Next goal: post-migration polish** — alphas, bibliography search, live-app verification; plus user confirmation of the patched books-tab speedup and background swap in a real session.

**Patch delivery (new, 2026-08-19):**
- Rebuild PYZ + in-place splice into the installed binary; total size unchanged.
- `across` gets a 12-byte prefix (`LOAD_CONST 0; LOAD_CONST None; IMPORT_NAME shamela_patch; LOAD_ATTR install; CALL_FUNCTION 0; POP_TOP` — level FIRST, fromlist second!) calling `install()` at first app import.
- Interception = sys.modules proxy shims (frozen importer beats any meta-path finder).
- Background lookup: `$SHAMELA_BG` → `bin/background.jpg|.png` → `~/.shamela/background.jpg|.png`.
- Books tab: `BookCache._getCache` → batch prefill (2 queries, exact `fillBookCache` replication) + re-prefill guard.
- Measure-only via `SHAMELA_BASELINE=1`; everything logs to `/tmp/shamela_boot.log`.

**Architecture facts (validated):**
- Golden (source): `Books/<shamelaID%10>/<shamelaID>.mdb` — Jet/Access keyed by old-official `shamelaID` (NOT golden `id`), tables `book(id,part,page,nass)` + `title(id,lvl,sub,tit)`, text **cp1256** (access_parser returns latin1-mojibake str → re-encode `latin1`→`cp1256`). Catalog: `book_index.db` `books(id,bookName,shamelaID,bookInfo,authorName,authorDeath,cat,...)`; `fields`/`fieldsBooks` empty.
- Modern (target): `database/master.db` catalog (`category` 41 rows, `book` ~30k rows, `author` ~5k, `author_book`); per-book `database/book/<id%1000:03d>/<id>.db` (`page(id,part,page,number,services)` + `title(id,page,parent)`, DDL identical to `connectBook`); **page/title text lives in Lucene `database/store/{page,title}`** — doc id `"{book_id}-{page_id}"`, fields `body`(TEXT), `m_body`/`n_body`(ANALYSE); `Book._getDoc` adds ORD sorters from `CoreDb().sorter(book_id)`. Bibliography/search stores: `book`/`s_book`/`author`/`s_author` (via `Importer.addBook/addAuthor`), `aya`, `esnad`.
- **ID spaces all differ:** golden `id` ≠ golden `shamelaID` ≠ modern `book_id`. Map by normalized title match (22.8% hit; covers 77% of modern ids).
- Browse uses SQLite joins (`categorizedBooks`/`arrangeBooks` order by category_order, book_date, author.alpha, book.alpha, group_order); `getOnline(1)` = `major_ondisk>0` (off-disk books hidden). Betaka/search reads Lucene `book`/`author` stores (empty for migration books until populated).
- `Importer.deleteBooks(ids)` deletes page/title/esnad docs by `book_key` (re-run safety). `Index.writer` caches one writer per index; commit per batch.
- Runtime: `d3/` first in `sys.path`, `decompiled/` fallback; stub `dbmanager` with `CoreDb.sorter`; boot = `Across.home_directory` + `lucene_version=2` + `jpype.startJVM(classpath=["<home>/app/lucene/2/*"])` + bundled JRE.
- Title quirks: golden `title` ids repeat → renumber + remap parents; `title.page` derived by startswith-match; golden `page`/`part` columns can be NULL → `_int()` guard; part `''` single-part else `str(part)`.

**Open items (next):**
- [ ] Re-apply alphas: run app's sort (alphaBooks/alphaAuthors) or set sensible per-author alphas for the ~22k new books/authors (browse currently unsorted by author).
- [ ] Populate bibliography/search Lucene stores (`book`/`s_book`/`author`/`s_author`) for new books via `Importer.addBook/addAuthor` (golden `bookInfo` as hint) so book/author search + betaka work.
- [ ] Verify in the live app UI (categories tree, parts combo, TOC, page text, search).
- [ ] Covers: golden has none; skip or map from `database/cover.db`.
- [ ] 44 pre-existing on-disk books skipped (teasers); decide whether to overwrite with golden content (`--force-ondisk`).

---

## Known Bugs

- [ ] `uncompyle6` cannot decompile ~6+ construct patterns in this codebase (see `systems.md` for the list) — every one must be rebuilt by hand from `xdis`/`dis` output *(found: 2026-08-14)*
- [ ] App launch under the dev environment logs `qt.qpa.plugin: Could not find the Qt platform plugin "wayland"` + fontconfig/font warnings (`shamela-run.log`) — environment issue to solve before any "run from source" attempt *(found: 2026-08-14)*

---

## Active TODOs

- [ ] Future edits: work in the REPO copies (`/mnt/airfryer/Projects/Linux/shamela-linux/{d3,decompiled}`) rather than `/tmp/opencode`, so nothing is lost on reboot *(added: 2026-08-14)*
- [ ] Run the failed-section fix pass over the remaining ~31 decompiled modules (only `customs`, `updater`, `options`, `shamela`, `displaybook`, `engine`, `ignore`, `searchboxes` are cleaned) — ongoing goal: finish the byte-exact source tree across all 39 modules *(added: 2026-08-14)*
- [ ] For each newly cleaned module: byte-verify every function, then `ast.parse` the whole file *(added: 2026-08-14)*
- [ ] Decide reconcile strategy: does `d3/` replace `decompiled/`, or should the cleaned files be copied back over the decompiled originals? *(added: 2026-08-14)*

---

## Planned Features

- [ ] Runtime restore: wire the byte-exact source into `dev-env/.venv` and launch the app from source instead of the frozen binary *(added: 2026-08-14)*
- [ ] Full-module bytecode equivalence audit (diff every function's `co_code` across all 39 modules) *(added: 2026-08-14)*
