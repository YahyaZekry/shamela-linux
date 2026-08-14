# uncompyle6 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.12 | packaged by conda-forge | (default, Oct 26 2021, 06:08:21) 
# [GCC 9.4.0]
# Embedded file name: scaling.py
"""
scaling.py — Single source of truth for all DPI / size / font scaling.

Usage
-----
Call ``init_scaling(screen)`` once, right after obtaining the primary screen
object in MainWindow.__init__.  After that use:

    scaled_font_size(pt)    – scale a base point-size for use in QFont / CSS

Design contract
---------------
* At 96 logical DPI (100 % Windows scaling) every function returns its
  input unchanged.  The "default value" is always 1.0 × the base size.
* There is ONE place (init_scaling) where platform/DPI logic lives.
  Tune it here; never add platform ternaries at call sites.
"""
from __future__ import annotations
_font_scale: 'float' = 1.0

def init_scaling(screen) -> 'None':
    """
    Compute and store scale factors from *screen* (a QScreen object).

    Call once from MainWindow.__init__ immediately after self.getScreen().

    All platforms use 96 logical DPI as the reference baseline (the Qt/Windows
    standard).  On macOS, Qt historically reported ~72 logical DPI, so we apply
    a documented correction factor (96/72 ≈ 1.333) to fonts only, keeping pixel
    dimensions consistent across platforms.

    If macOS behaviour still looks wrong after upgrading Qt, adjust ONLY the
    MAC_FONT_FACTOR constant below — not the individual call sites.
    """
    global _font_scale
    REFERENCE_DPI = 96.0
    MAC_FONT_FACTOR = REFERENCE_DPI / 72.0 * 1.3
    try:
        logical_dpi = screen.logicalDotsPerInch()
    except Exception:
        logical_dpi = REFERENCE_DPI

    ui_scale = logical_dpi / REFERENCE_DPI
    from across import Across
    if Across.os == 'mac':
        _font_scale = ui_scale * MAC_FONT_FACTOR
    else:
        _font_scale = ui_scale


def scaled_font_size(base_pt: 'int | float') -> 'int':
    """
    Scale a font point-size.

    *base_pt* is the intended size at the reference 96 DPI / 100 % scaling.
    Pass plain integers; do NOT pre-multiply with any scale factor.
    """
    return max(1, round(base_pt * _font_scale))