# Shamela App Patch — post-install customization

Injects runtime fixes into the *installed* (PyInstaller-frozen) Shamela binary
by splicing a rebuilt `PYZ-00.pyz` back into the executable in place —
no PyInstaller rebuild needed, total file size unchanged.

## What the patch does

1. **Start-screen background image** — `MainWindow.showBackground` loads an
   external file instead of the bundled `:/images/background.jpg`.
   Lookup order: `$SHAMELA_BG` → `<bin>/background.jpg` → `<bin>/background.png`
   → `~/.shamela/background.jpg` → `~/.shamela/background.png`.
2. **Fast books tab** — `BookCache._getCache` batch-prefills the whole book
   catalog (2 SQL queries: all books + all authors) instead of opening a fresh
   SQLite connection + per-author queries for every book (`CoreDb().fillBookCache`)
   on each cache miss. Replicates the original tuple exactly (arabize,
   per-type icon paths, `(ت year)` deaths, joinAuthors).
3. **Timing instrumentation** — wrappers around `MainWindow.__init__/show/showbiblio`,
   `BookList._loadItems`, `CoreDb.getBooks/getBooksSet/getCategories` log to
   `/tmp/shamela_boot.log`. Set `SHAMELA_BASELINE=1` for measure-only mode.

## How it's implemented

- `surgery.py` — reads the installed binary, patches the `across` module by
  bytecode to run `import shamela_patch; shamela_patch.install()` at the very
  first app import, adds `shamela_patch` to the PYZ, rebuilds the PYZ (zlib 9),
  pads to the original size, splices it in place, writes `<exe>.new`.
- `shamela_patch.py` — the injected module. Intercepts app module loads via
  `sys.modules` proxy shims (the frozen importer wins over any meta-path
  finder, so shims must be pre-registered in `sys.modules`).
- `pyz_tool.py` — CArchive + PYZ parser (data base = archive_start + 88;
  TOC at cookie_pos − toc_length; PYZ TOC is a marshal dict at `data[toc_offset:]`).

Bytecode specifics learned the hard way (keep!):
- Every 3.6+ instruction is 2 bytes (`POP_TOP` = `01 00`).
- `IMPORT_NAME` pops `fromlist` (top), reads `level` beneath it: compile order
  is `LOAD_CONST <level=0>` then `LOAD_CONST <fromlist=None>`.

## Reapply after app reinstall

```bash
# 1. restore/point at the fresh binary:
#    cp <fresh>/app/linux/64/bin/shamela /home/monst3r/Apps/shamela/app/linux/64/bin/shamela? 
#    simplest: EXE_IN/EXE_OUT are hardcoded in surgery.py — edit if app moved.

# 2. build + test WITHOUT touching the live binary:
/mnt/airfryer/Projects/Linux/shamela-linux/dev-env/.venv/bin/python \
  /mnt/airfryer/Projects/Linux/shamela-linux/patch/surgery.py

# 3. swap in and verify boot (should take <5s to first log lines):
cd /home/monst3r/Apps/shamela/app/linux/64/bin
mv shamela shamela.orig-bak && mv shamela.new shamela && chmod +x shamela
rm -f /tmp/shamela_boot.log
timeout 60 ./shamela & sleep 20; cat /tmp/shamela_boot.log

# 4. drop your background image at bin/background.jpg (or ~/.shamela/background.jpg)
```

`surgery.py` MUST run under `dev-env/.venv/bin/python` (CPython 3.7.12) —
marshal/bytecode must match the frozen runtime.