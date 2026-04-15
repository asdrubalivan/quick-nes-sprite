#!/usr/bin/env python3
"""
gen_chr.py — Generates chr/sprites.chr for quick-nes-sprite.

CHR-ROM layout (8192 bytes = 512 tiles x 16 bytes):
  Pattern Table 0 ($0000-$0FFF): background tiles (tiles $00-$FF)
  Pattern Table 1 ($1000-$1FFF): sprite tiles    (tiles $00-$FF)

Each tile is 16 bytes:
  bytes  0-7  : bit-plane 0 (low bit of each pixel's 2-bit color)
  bytes  8-15 : bit-plane 1 (high bit of each pixel's 2-bit color)

Within each byte: bit 7 = leftmost pixel, bit 0 = rightmost pixel.

Resulting pixel colors:
  color 0 (transparent/bg) : plane0=0, plane1=0
  color 1                  : plane0=1, plane1=0
  color 2                  : plane0=0, plane1=1
  color 3                  : plane0=1, plane1=1
"""

import pathlib

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def tile(plane0: list[int], plane1: list[int]) -> bytes:
    """Build a 16-byte NES tile from two 8-element lists."""
    assert len(plane0) == 8, "plane0 must have 8 bytes"
    assert len(plane1) == 8, "plane1 must have 8 bytes"
    return bytes(plane0 + plane1)


def solid_tile(color: int) -> bytes:
    """Return a tile filled entirely with *color* (0-3)."""
    p0 = 0xFF if (color & 1) else 0x00
    p1 = 0xFF if (color & 2) else 0x00
    return tile([p0] * 8, [p1] * 8)


EMPTY_TILE = tile([0x00] * 8, [0x00] * 8)  # all color-0 (transparent)

# ---------------------------------------------------------------------------
# Pattern Table 0 — background tiles
# ---------------------------------------------------------------------------

# Tile $00 — empty sky (all transparent / color 0)
bg_00_sky = EMPTY_TILE

# Tile $01 — ground / grass
# Rows 0-1 = color 3 (dark green), rows 2-7 = color 1 (green)
# plane0: 1 everywhere → $FF for all 8 rows
# plane1: 1 for rows 0-1, 0 for rows 2-7
bg_01_ground = tile(
    plane0=[0xFF] * 8,
    plane1=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $02 — tree trunk
# Color 1 (brown) in center columns (bits 5-2 set → 0b00111100 = $3C)
# Last row = full base ($FF)
bg_02_trunk = tile(
    plane0=[0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0xFF],
    plane1=[0x00] * 8,
)

# Tile $03 — tree foliage (color 2 = dark green, circular shape)
bg_03_foliage = tile(
    plane0=[0x00] * 8,
    plane1=[0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C, 0x18],
)

# Tile $04 — Venezuela flag: yellow stripe (color 1, solid)
bg_04_flag_yellow = solid_tile(1)

# Tile $05 — Venezuela flag: blue stripe with white stars
# Background = color 2 (blue): plane0=0, plane1=1
# Stars      = color 3 (white): plane0=1, plane1=1
# Star pixel map (1 = star position):
#   Row 0: 0 0 0 0 0 0 0 0  = 0x00
#   Row 1: 0 1 0 1 0 1 0 0  = 0x54
#   Row 2: 1 0 0 0 0 0 1 0  = 0x82
#   Row 3: 0 0 0 0 0 0 0 0  = 0x00
#   Row 4: 1 0 0 0 0 0 1 0  = 0x82
#   Row 5: 0 1 0 1 0 1 0 0  = 0x54
#   Row 6: 0 0 0 0 0 0 0 0  = 0x00
#   Row 7: 0 0 0 0 0 0 0 0  = 0x00
_stars = [0x00, 0x54, 0x82, 0x00, 0x82, 0x54, 0x00, 0x00]
bg_05_flag_blue = tile(
    plane0=_stars,                # 1 where stars are (color 3 needs plane0=1)
    plane1=[0xFF] * 8,            # 1 everywhere (blue bg OR white star)
)

# Tile $06 — Venezuela flag: red stripe (color 3, solid)
bg_06_flag_red = solid_tile(3)

# Collect all background tiles; tiles $07-$FF are zeroed
BG_TILES: dict[int, bytes] = {
    0x00: bg_00_sky,
    0x01: bg_01_ground,
    0x02: bg_02_trunk,
    0x03: bg_03_foliage,
    0x04: bg_04_flag_yellow,
    0x05: bg_05_flag_blue,
    0x06: bg_06_flag_red,
}

# ---------------------------------------------------------------------------
# Pattern Table 1 — sprite tiles
# ---------------------------------------------------------------------------
# Capybara: 3x3 tile arrangement (24x24 px), 2 animation frames.
#
# Frame 0: tiles $00-$08  (TL TC TR / ML MC MR / BL BC BR)
# Frame 1: tiles $09-$11  (same layout; only BL/BC differ — legs animate)
#
# Pixel color encoding:
#   0 = transparent   (plane0=0, plane1=0)
#   1 = dark brown    (plane0=1, plane1=0)  — outline / eye / feet
#   2 = tan body      (plane0=0, plane1=1)  — body fill
#
# Within each tile byte: bit7 = leftmost column of that tile, bit0 = rightmost.
#
# Full 24x24 pixel grid (cols 0-23, rows 0-23):
#
#    TL = cols  0-7   TC = cols  8-15   TR = cols 16-23
#    ML = cols  0-7   MC = cols  8-15   MR = cols 16-23
#    BL = cols  0-7   BC = cols  8-15   BR = cols 16-23
#
#       TL (c0-c7)             TC (c8-c15)           TR (c16-c23)
# r0:   0  0  1  1  0  1  1  0 | 0  0  0  0  0  0  0  0 | 0  0  0  0  0  0  0  0  (two ears)
# r1:   0  1  2  2  1  2  2  1 | 0  0  0  0  0  0  0  0 | 0  0  0  0  0  0  0  0  (ear fills)
# r2:   1  2  2  2  2  2  2  2 | 1  0  0  0  0  0  0  0 | 0  0  0  0  0  0  0  0  (head)
# r3:   1  2  1  2  2  2  2  2 | 2  2  2  1  0  0  0  0 | 0  0  0  0  0  0  0  0  (eye@c2)
# r4:   1  2  2  2  2  2  2  2 | 2  2  2  2  2  1  0  0 | 0  0  0  0  0  0  0  0
# r5:   1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  1  0 | 0  0  0  0  0  0  0  0
# r6:   1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 1  0  0  0  0  0  0  0
# r7:   1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 2  1  0  0  0  0  0  0
#
#       ML (c0-c7)             MC (c8-c15)           MR (c16-c23)
# r8:   1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 2  2  1  0  0  0  0  0
# r9:   1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 2  2  1  0  0  0  0  0
# r10:  1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 2  2  1  0  0  0  0  0
# r11:  1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 2  1  0  0  0  0  0  0
# r12:  1  2  2  2  2  2  2  2 | 2  2  2  2  2  2  2  2 | 1  0  0  0  0  0  0  0
# r13:  1  1  2  2  2  2  2  2 | 2  2  2  2  2  2  1  0 | 0  0  0  0  0  0  0  0  (snout top)
# r14:  1  2  1  2  2  2  2  2 | 2  2  2  2  1  0  0  0 | 0  0  0  0  0  0  0  0  (snout detail)
# r15:  0  1  2  2  1  0  0  0 | 0  0  0  1  0  0  0  0 | 0  0  0  0  0  0  0  0  (snout bottom)
#
#       BL (c0-c7)             BC (c8-c15)           BR (c16-c23)
# r16:  0  0  1  0  0  0  0  0 | 0  0  1  0  0  0  0  0 | 0  0  0  0  0  0  0  0  (nose/rump)
# r17:  0  0  0  1  2  0  1  2 | 0  1  2  0  1  2  0  0 | 0  0  0  0  0  0  0  0  (front|back legs f0)
# r18:  0  0  0  1  2  0  1  2 | 0  1  2  0  1  2  0  0 | 0  0  0  0  0  0  0  0
# r19:  0  0  0  1  1  0  1  1 | 0  1  1  0  1  1  0  0 | 0  0  0  0  0  0  0  0  (feet f0)
# r20:  0  0  0  0  0  0  0  0 | 0  0  0  0  0  0  0  0 | 0  0  0  0  0  0  0  0
# r21-r23: all transparent
#
# Frame 1 BL: legs shift 1 px right (c4-c5, c6-c7)
# r17:  0  0  0  0  1  2  1  2 | ...
# r19:  0  0  0  0  1  1  1  1 | ...
# Frame 1 BC: back legs shift 1 px right (c10-c11, c13-c14)
# r17:  0  0  1  2  0  1  2  0 | ...
# r19:  0  0  1  1  0  1  1  0 | ...
# ---------------------------------------------------------------------------

# ===========================================================================
# FRAME 0  — tiles $00-$08
# ===========================================================================

# Tile $00 — TL (cols 0-7, rows 0-7)
# r0: 0 0 1 1 0 1 1 0  p0: c2(b5),c3(b4),c5(b2),c6(b1)=0x36  p1=0x00
# r1: 0 1 2 2 1 2 2 1  p0: c1(b6),c4(b3),c7(b0)=0x49  p1: c2(b5),c3(b4),c5(b2),c6(b1)=0x36
# r2: 1 2 2 2 2 2 2 2  p0: c0(b7)=0x80  p1: c1-c7(b6-b0)=0x7F
# r3: 1 2 1 2 2 2 2 2  p0: c0(b7),c2(b5)=0xA0  p1: c1(b6),c3-c7(b4-b0)=0x5F
# r4-r7: 1 2 2 2 2 2 2 2  p0=0x80 p1=0x7F
spr_00_tl_f0 = tile(
    plane0=[0x36, 0x49, 0x80, 0xA0, 0x80, 0x80, 0x80, 0x80],
    plane1=[0x00, 0x36, 0x7F, 0x5F, 0x7F, 0x7F, 0x7F, 0x7F],
)

# Tile $01 — TC (cols 8-15, rows 0-7)
# Body is FULL WIDTH from row 2 (no diagonal growth — fixes the triangle look).
# r0-r1: transparent (ears in TL stick above body here)
# r2-r7: all tan (c8-c15 = body fill, outline is in TR tile at c16)
# p0=0x00 (no color-1 pixels), p1=0xFF (all color-2)
spr_01_tc_f0 = tile(
    plane0=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    plane1=[0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],
)

# Tile $02 — TR (cols 16-23, rows 0-7)
# Right-side body outline: only c16 (bit7 of TR) is drawn.
# r0-r1: transparent
# r2-r7: outline at c16 only → p0=0x80 (bit7=1), p1=0x00
spr_02_tr_f0 = tile(
    plane0=[0x00, 0x00, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80],
    plane1=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $03 — ML (cols 0-7, rows 8-15)
# r8-r12: 1 2 2 2 2 2 2 2  p0=0x80 p1=0x7F
# r13: 1 1 2 2 2 2 2 2  p0: c0(b7),c1(b6)=0xC0  p1: c2-c7(b5-b0)=0x3F
# r14: 1 2 1 2 2 2 2 2  p0: c0(b7),c2(b5)=0xA0  p1: c1(b6),c3-c7(b4-b0)=0x5F
# r15: 0 1 2 2 1 0 0 0  p0: c1(b6),c4(b3)=0x48  p1: c2(b5),c3(b4)=0x30
spr_03_ml_f0 = tile(
    plane0=[0x80, 0x80, 0x80, 0x80, 0x80, 0xC0, 0xA0, 0x48],
    plane1=[0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x3F, 0x5F, 0x30],
)

# Tile $04 — MC (cols 8-15, rows 8-15)
# r8-r12: all 2  p0=0x00 p1=0xFF
# r13: 2 2 2 2 2 2 1 0  c14=1 → p0: c14(b1)=0x02  p1: c8-c13(b7-b2)=0xFC
# r14: 2 2 2 2 1 0 0 0  c12=1 → p0: c12(b3)=0x08  p1: c8-c11(b7-b4)=0xF0
# r15: 0 0 0 1 0 0 0 0  c11=1 → p0: c11(b4)=0x10  p1=0x00
spr_04_mc_f0 = tile(
    plane0=[0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x08, 0x10],
    plane1=[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC, 0xF0, 0x00],
)

# Tile $05 — MR (cols 16-23, rows 8-15)
# Right-side body outline only at c16 (same width as TR tile above it).
# r8-r12: outline at c16 only → p0=0x80 (bit7=1), p1=0x00
# r13-r15: transparent (body tapers in ML/MC tiles at those rows)
spr_05_mr_f0 = tile(
    plane0=[0x80, 0x80, 0x80, 0x80, 0x80, 0x00, 0x00, 0x00],
    plane1=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $06 — BL (cols 0-7, rows 16-23) — frame 0 legs
# r16: 0 0 1 0 0 0 0 0  c2=1 → p0: c2(b5)=0x20  p1=0x00
# r17: 0 0 0 1 2 0 1 2  c3=1,c4=2,c6=1,c7=2 → p0: c3(b4),c6(b1)=0x12  p1: c4(b3),c7(b0)=0x09
# r18: same as r17
# r19: 0 0 0 1 1 0 1 1  c3=1,c4=1,c6=1,c7=1 → p0: c3(b4),c4(b3),c6(b1),c7(b0)=0x1B  p1=0x00
# r20-r23: all 0
spr_06_bl_f0 = tile(
    plane0=[0x20, 0x12, 0x12, 0x1B, 0x00, 0x00, 0x00, 0x00],
    plane1=[0x00, 0x09, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $07 — BC (cols 8-15, rows 16-23) — frame 0 legs
# In BC: c8=bit7, c9=bit6, c10=bit5, c11=bit4, c12=bit3, c13=bit2, c14=bit1, c15=bit0
# r16: 0 0 1 0 0 0 0 0  c10=1 → p0: c10(b5)=0x20  p1=0x00
# r17: 0 1 2 0 1 2 0 0  c9=1,c10=2,c12=1,c13=2 → p0: c9(b6),c12(b3)=0x48  p1: c10(b5),c13(b2)=0x24
# r18: same as r17
# r19: 0 1 1 0 1 1 0 0  c9=1,c10=1,c12=1,c13=1 → p0: c9(b6),c10(b5),c12(b3),c13(b2)=0x6C  p1=0x00
# r20-r23: all 0
spr_07_bc_f0 = tile(
    plane0=[0x20, 0x48, 0x48, 0x6C, 0x00, 0x00, 0x00, 0x00],
    plane1=[0x00, 0x24, 0x24, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $08 — BR (cols 16-23, rows 16-23) — empty
spr_08_br_f0 = EMPTY_TILE

# ===========================================================================
# FRAME 1 — body identical, only BL/BC differ (legs walking cycle)
# ===========================================================================

# Tiles $09-$0E: top and middle rows identical to frame 0
spr_09_tl_f1 = spr_00_tl_f0
spr_0a_tc_f1 = spr_01_tc_f0
spr_0b_tr_f1 = spr_02_tr_f0
spr_0c_ml_f1 = spr_03_ml_f0
spr_0d_mc_f1 = spr_04_mc_f0
spr_0e_mr_f1 = spr_05_mr_f0

# Tile $0F — BL frame 1: legs shift 1 px right (c4-c5 and c6-c7)
# r16: 0 0 1 0 0 0 0 0  same nose → p0=0x20 p1=0x00
# r17: 0 0 0 0 1 2 1 2  c4=1,c5=2,c6=1,c7=2 → p0: c4(b3),c6(b1)=0x0A  p1: c5(b2),c7(b0)=0x05
# r18: same as r17
# r19: 0 0 0 0 1 1 1 1  c4-c7=1 → p0: c4(b3),c5(b2),c6(b1),c7(b0)=0x0F  p1=0x00
spr_0f_bl_f1 = tile(
    plane0=[0x20, 0x0A, 0x0A, 0x0F, 0x00, 0x00, 0x00, 0x00],
    plane1=[0x00, 0x05, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $10 — BC frame 1: back legs shift 1 px right (c10-c11 and c13-c14)
# r16: same rump → p0=0x20 p1=0x00
# r17: 0 0 1 2 0 1 2 0  c10=1,c11=2,c13=1,c14=2 → p0: c10(b5),c13(b2)=0x24  p1: c11(b4),c14(b1)=0x12
# r18: same as r17
# r19: 0 0 1 1 0 1 1 0  c10=1,c11=1,c13=1,c14=1 → p0: c10(b5),c11(b4),c13(b2),c14(b1)=0x36  p1=0x00
spr_10_bc_f1 = tile(
    plane0=[0x20, 0x24, 0x24, 0x36, 0x00, 0x00, 0x00, 0x00],
    plane1=[0x00, 0x12, 0x12, 0x00, 0x00, 0x00, 0x00, 0x00],
)

# Tile $11 — BR frame 1: empty (same as frame 0)
spr_11_br_f1 = EMPTY_TILE

SPR_TILES: dict[int, bytes] = {
    # Frame 0 (base = $00)
    0x00: spr_00_tl_f0,
    0x01: spr_01_tc_f0,
    0x02: spr_02_tr_f0,
    0x03: spr_03_ml_f0,
    0x04: spr_04_mc_f0,
    0x05: spr_05_mr_f0,
    0x06: spr_06_bl_f0,
    0x07: spr_07_bc_f0,
    0x08: spr_08_br_f0,
    # Frame 1 (base = $09)
    0x09: spr_09_tl_f1,
    0x0A: spr_0a_tc_f1,
    0x0B: spr_0b_tr_f1,
    0x0C: spr_0c_ml_f1,
    0x0D: spr_0d_mc_f1,
    0x0E: spr_0e_mr_f1,
    0x0F: spr_0f_bl_f1,
    0x10: spr_10_bc_f1,
    0x11: spr_11_br_f1,
}

# ---------------------------------------------------------------------------
# Assemble CHR-ROM
# ---------------------------------------------------------------------------

CHR_SIZE = 8192          # bytes
TILE_SIZE = 16           # bytes per tile
PT0_OFFSET = 0           # Pattern Table 0 starts at byte 0
PT1_OFFSET = 4096        # Pattern Table 1 starts at byte 4096

chr_data = bytearray(CHR_SIZE)  # initialized to all zeros

# Write pattern table 0 tiles
for tile_idx, tile_data in BG_TILES.items():
    offset = PT0_OFFSET + tile_idx * TILE_SIZE
    chr_data[offset:offset + TILE_SIZE] = tile_data

# Write pattern table 1 tiles
for tile_idx, tile_data in SPR_TILES.items():
    offset = PT1_OFFSET + tile_idx * TILE_SIZE
    chr_data[offset:offset + TILE_SIZE] = tile_data

# ---------------------------------------------------------------------------
# Write output file
# ---------------------------------------------------------------------------

output_path = pathlib.Path(__file__).parent.parent / "chr" / "sprites.chr"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_bytes(chr_data)

print(f"Written: {output_path}")
print(f"Size   : {len(chr_data)} bytes")
assert len(chr_data) == CHR_SIZE, f"Expected {CHR_SIZE} bytes, got {len(chr_data)}"
print("OK — file is exactly 8192 bytes.")
