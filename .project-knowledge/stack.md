# Stack

> Part of shamela-linux/.project-knowledge/ | Last updated: 2026-08-14

## Tech Stack

| Category | Details |
|----------|---------|
| Target language | Python 3.7.12 (CPython 3.7m, x86_64 — `cpython-37m-x86_64-linux-gnu`) |
| App framework | PyQt / Qt widgets (QTextBrowser, QPlainTextEdit, QSplitter, …) — PyInstaller-frozen |
| App version | Shamela Library Linux 1448.2 |
| Packaging | PyInstaller one-folder build; main `shamela` launcher + PYZ-00.pyz archive |
| Decompilers | uncompyle6 3.9.0, decompyle3 3.9.0, xdis 6.0.5 (spark_parser dep) |
| Runtime env | conda-style venv at `dev-env/.venv` (Python 3.7.12), manually built Py3.7 + Qt libs |
| OS | Linux x86_64 |

## Dev Commands

| Command | What It Does |
|---------|-------------|
| `dev-env/.venv/bin/uncompyle6 file.pyc` | Decompile a single .pyc to source |
| `dev-env/.venv/bin/python -m xdis …` | xdis CLI (marshal/load inspection) |
| `dev-env/.venv/bin/python` | Run scripts using `xdis.load_module` + `dis` for bytecode analysis |
| `dev-env/.venv/bin/python -m py_compile file.py` | Syntax-check reconstructed source |
| `MAMBA_ROOT_PREFIX=$HOME/micromamba-root` | Env var required to activate the conda-style venv |

## Verification recipe (byte-exactness)

Ground-truth check that a reconstructed function matches the original:

1. `load_module()` the original `.pyc` with xdis → walk `co_consts` to find the code object by `co_name`.
2. `compile()` the reconstructed source file → walk the same way.
3. Compare `co_code` (raw bytecode). Identical `co_code` = exact reconstruction (line numbers live in a separate table and don't affect it).

Also confirmed empirically: Python 3.7's exact bytecode for a construct (e.g. `f(a, b, kw=x)` → `CALL_FUNCTION_KW`; `x or y` → `JUMP_IF_TRUE_OR_POP`; chained `A <= b <= C` → `DUP_TOP/ROT_THREE`) is checked with a throwaway `dis.dis()` probe before trusting the decompiler's guess.

---

## Environment Variables

| Variable | Used In | What It Enables |
|----------|---------|----------------|
| `MAMBA_ROOT_PREFIX` | venv activation | Resolves the conda root so the Py3.7 env initializes |
