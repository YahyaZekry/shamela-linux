# Shamela Linux Restoration — Knowledge Index

> Last updated: 2026-08-14 (artifacts persisted; DB-mount goal set)
> Status: Active
> Stack: Python 3.7 (CPython 3.7.12) · PyInstaller-frozen · Qt widgets · xdis 6.0.5 / uncompyle6 3.9.0
> Current goal: Mount the user's existing Windows Shamela database in the restored Linux build

## What This Project Does

Reverse-engineers the Shamela Library Linux desktop app (v1448.2, a PyInstaller-frozen
Python 3.7.12 Qt application) into clean, editable Python source. The acceptance bar is
byte-exactness: each reconstructed function must compile to bytecode (`co_code`) identical
to the original `.pyc`, using xdis/uncompyle6 and manual disassembly reconstruction where the
decompiler fails.

---

## Files in This Folder

| File | Contents | Load when... |
|------|----------|--------------|
| `stack.md` | Toolchain, venv, dev commands, env vars | Setting up, running decompile/verify commands |
| `structure.md` | Where every artifact lives (tar, extract, decompiled, d3) | Navigating directories, adding new modules |
| `systems.md` | The decompile→verify→rebuild pipeline stages | Planning pipeline work |
| `features.md` | App feature surface + project deliverables | Understanding what's built vs. remaining |
| `roadmap.md` | Current goal, known bugs, TODOs | Starting any task — know what's in flight |
| `history.md` | Fixed functions, decisions, removed stubs | Debugging, reviewing past choices |
| `sessions.md` | Session-by-session log | Reviewing work history |

---

## Context Loading Guide

| Task | Load these files |
|------|-----------------|
| Continue fixing failed decompilation sections | `roadmap.md` + `history.md` + `stack.md` |
| Verify a reconstructed function | `stack.md` + `history.md` |
| Add a new module to the d3 tree | `structure.md` + `roadmap.md` |
| Try running the app from source | `stack.md` + `features.md` + `roadmap.md` |
| General orientation (new session) | This file → then pick by task |
| Full audit | All files |

---

*Maintained with [project-knowledge](https://github.com/YahyaZekry/claude-code-skills) · by [Yahya Zekry](https://github.com/YahyaZekry/claude-code-skills)*
