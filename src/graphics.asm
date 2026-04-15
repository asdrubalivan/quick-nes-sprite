; graphics.asm - PPU palette and nametable routines

; ============================================================
; write_palettes
; Writes all 8 palettes (BG + Sprite) to PPU $3F00-$3F1F
; ============================================================
.proc write_palettes
    ; Reset the PPU address latch
    LDA PPUSTATUS

    ; Set PPU address to $3F00 (palette RAM start)
    LDA #$3F
    STA PPUADDR
    LDA #$00
    STA PPUADDR

    ; --- BG Palette 0 ($3F00): negro, verde, marron, beige ---
    LDA #$0F
    STA PPUDATA
    LDA #$29
    STA PPUDATA
    LDA #$17
    STA PPUDATA
    LDA #$36
    STA PPUDATA

    ; --- BG Palette 1 ($3F04): negro, amarillo, azul, rojo ---
    LDA #$0F
    STA PPUDATA
    LDA #$28
    STA PPUDATA
    LDA #$12
    STA PPUDATA
    LDA #$16
    STA PPUDATA

    ; --- BG Palette 2 ($3F08): negro, verde oscuro, verde claro, blanco grisaceo ---
    LDA #$0F
    STA PPUDATA
    LDA #$1A
    STA PPUDATA
    LDA #$09
    STA PPUDATA
    LDA #$20
    STA PPUDATA

    ; --- BG Palette 3 ($3F0C): unused ---
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA

    ; --- SP Palette 0 ($3F10): negro, marron, tan, blanco ---
    LDA #$0F
    STA PPUDATA
    LDA #$17
    STA PPUDATA
    LDA #$27
    STA PPUDATA
    LDA #$30
    STA PPUDATA

    ; --- SP Palette 1 ($3F14): unused ---
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA

    ; --- SP Palette 2 ($3F18): unused ---
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA

    ; --- SP Palette 3 ($3F1C): unused ---
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA
    LDA #$0F
    STA PPUDATA

    RTS
.endproc

; ============================================================
; set_ppu_addr_row_col
; Helper: set PPU address to $2000 + row*32 + col
; Inputs: A = row (0-29), X = col (0-31)
; Clobbers: A, X
; ============================================================
.proc set_ppu_addr_row_col
    ; Compute high byte: $20 + (row >> 3), low byte: (row << 5) | col
    ; row * 32 = row << 5.  Max row=29, 29*32 = 928 = $03A0
    ; High byte of ($2000 + offset): $20 | (offset >> 8)
    ; Low byte: offset & $FF
    ; We use a temp approach: store row in temp, multiply
    ; For simplicity, use the accumulator approach with a loop.
    ; Actually we'll inline this per row in write_nametable. RTS placeholder.
    RTS
.endproc

; ============================================================
; write_nametable
; Writes the full 32x30 nametable to PPU $2000, then
; writes attribute bytes to $23C0.
;
; Tile index legend:
;   $00 = sky (empty)
;   $01 = ground/grass
;   $02 = tree trunk
;   $03 = tree foliage
;   $04 = flag stripe yellow
;   $05 = flag stripe blue
;   $06 = flag stripe red
; ============================================================
.proc write_nametable
    ; Reset PPU latch and set address to $2000
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$00
    STA PPUADDR

    ; --- Write 30 rows x 32 cols = 960 bytes ---
    ; We write row by row. Default tile is $00 (sky).
    ; Rows 0-26: sky ($00), with patches for flag and trees
    ; Rows 27-29: ground ($01)
    ;
    ; Strategy:
    ;   1. Fill entire nametable with $00 (sky)
    ;   2. Then patch specific cells by seeking + writing

    ; Step 1: Fill all 960 bytes with $00
    LDX #$00
    LDA #$00
@fill_nt_lo:
    STA PPUDATA
    INX
    BNE @fill_nt_lo
    ; X wrapped to 0, we've written 256 bytes. Need 960 total = 256*3 + 192
    ; Second 256 bytes
    LDX #$00
@fill_nt_lo2:
    STA PPUDATA
    INX
    BNE @fill_nt_lo2
    ; Third 256 bytes
    LDX #$00
@fill_nt_lo3:
    STA PPUDATA
    INX
    BNE @fill_nt_lo3
    ; Remaining 192 bytes (960 - 768 = 192)
    LDX #$00
@fill_nt_lo4:
    STA PPUDATA
    INX
    CPX #$C0
    BNE @fill_nt_lo4

    ; Fill attribute table (64 bytes) with $00 (palette 0 everywhere)
    LDX #$00
    LDA #$00
@fill_attr:
    STA PPUDATA
    INX
    CPX #$40
    BNE @fill_attr

    ; -------------------------------------------------------
    ; Step 2: Patch specific tiles
    ; For each patch: seek PPU addr, write tile
    ; PPU addr for row R, col C = $2000 + R*32 + C
    ; -------------------------------------------------------

    ; --- Flag: cols 26-29, rows 0-1: yellow ($04) ---
    ; Row 0, col 26 = $2000 + 0*32 + 26 = $201A
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$1A
    STA PPUADDR
    LDA #$04
    STA PPUDATA   ; row 0, col 26
    STA PPUDATA   ; row 0, col 27
    STA PPUDATA   ; row 0, col 28
    STA PPUDATA   ; row 0, col 29

    ; Row 1, col 26 = $2000 + 1*32 + 26 = $203A
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$3A
    STA PPUADDR
    LDA #$04
    STA PPUDATA   ; row 1, col 26
    STA PPUDATA   ; row 1, col 27
    STA PPUDATA   ; row 1, col 28
    STA PPUDATA   ; row 1, col 29

    ; --- Flag: cols 26-29, row 2: blue ($05) ---
    ; Row 2, col 26 = $2000 + 2*32 + 26 = $205A
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$5A
    STA PPUADDR
    LDA #$05
    STA PPUDATA   ; row 2, col 26
    STA PPUDATA   ; row 2, col 27
    STA PPUDATA   ; row 2, col 28
    STA PPUDATA   ; row 2, col 29

    ; --- Flag: cols 26-29, row 3: red ($06) ---
    ; Row 3, col 26 = $2000 + 3*32 + 26 = $207A
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$7A
    STA PPUADDR
    LDA #$06
    STA PPUDATA   ; row 3, col 26
    STA PPUDATA   ; row 3, col 27
    STA PPUDATA   ; row 3, col 28
    STA PPUDATA   ; row 3, col 29

    ; --- Tree 1 at col 5: foliage rows 4-5, trunk rows 6-7 ---
    ; Row 4, col 5 = $2000 + 4*32 + 5 = $2085
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$85
    STA PPUADDR
    LDA #$03
    STA PPUDATA   ; row 4, col 5

    ; Row 5, col 5 = $2000 + 5*32 + 5 = $20A5
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$A5
    STA PPUADDR
    LDA #$03
    STA PPUDATA   ; row 5, col 5

    ; Row 6, col 5 = $2000 + 6*32 + 5 = $20C5
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$C5
    STA PPUADDR
    LDA #$02
    STA PPUDATA   ; row 6, col 5

    ; Row 7, col 5 = $2000 + 7*32 + 5 = $20E5
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$E5
    STA PPUADDR
    LDA #$02
    STA PPUDATA   ; row 7, col 5

    ; --- Tree 2 at col 15: foliage rows 4-5, trunk rows 6-7 ---
    ; Row 4, col 15 = $2000 + 4*32 + 15 = $208F
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$8F
    STA PPUADDR
    LDA #$03
    STA PPUDATA   ; row 4, col 15

    ; Row 5, col 15 = $2000 + 5*32 + 15 = $20AF
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$AF
    STA PPUADDR
    LDA #$03
    STA PPUDATA   ; row 5, col 15

    ; Row 6, col 15 = $2000 + 6*32 + 15 = $20CF
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$CF
    STA PPUADDR
    LDA #$02
    STA PPUDATA   ; row 6, col 15

    ; Row 7, col 15 = $2000 + 7*32 + 15 = $20EF
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$EF
    STA PPUADDR
    LDA #$02
    STA PPUDATA   ; row 7, col 15

    ; --- Tree 3 at col 22: foliage rows 4-5, trunk rows 6-7 ---
    ; Row 4, col 22 = $2000 + 4*32 + 22 = $2096
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$96
    STA PPUADDR
    LDA #$03
    STA PPUDATA   ; row 4, col 22

    ; Row 5, col 22 = $2000 + 5*32 + 22 = $20B6
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$B6
    STA PPUADDR
    LDA #$03
    STA PPUDATA   ; row 5, col 22

    ; Row 6, col 22 = $2000 + 6*32 + 22 = $20D6
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$D6
    STA PPUADDR
    LDA #$02
    STA PPUDATA   ; row 6, col 22

    ; Row 7, col 22 = $2000 + 7*32 + 22 = $20F6
    LDA PPUSTATUS
    LDA #$20
    STA PPUADDR
    LDA #$F6
    STA PPUADDR
    LDA #$02
    STA PPUDATA   ; row 7, col 22

    ; --- Ground: rows 27-29, all 32 cols (tile $01) ---
    ; Row 27, col 0 = $2000 + 27*32 + 0 = $2000 + $0360 = $2360
    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$60
    STA PPUADDR
    LDA #$01
    LDX #$00
@ground_row27:
    STA PPUDATA
    INX
    CPX #$20
    BNE @ground_row27

    ; Row 28, col 0 = $2000 + 28*32 = $2000 + $0380 = $2380
    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$80
    STA PPUADDR
    LDA #$01
    LDX #$00
@ground_row28:
    STA PPUDATA
    INX
    CPX #$20
    BNE @ground_row28

    ; Row 29, col 0 = $2000 + 29*32 = $2000 + $03A0 = $23A0
    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$A0
    STA PPUADDR
    LDA #$01
    LDX #$00
@ground_row29:
    STA PPUDATA
    INX
    CPX #$20
    BNE @ground_row29

    ; -------------------------------------------------------
    ; Step 3: Write attribute table ($23C0-$23FF)
    ; Attribute table layout: 8x8 bytes, each byte covers
    ; a 4x4 tile block (2x2 attribute regions of 2x2 tiles).
    ; Byte format: [BR|BL|TR|TL] -> bits 7-6, 5-4, 3-2, 1-0
    ; where TL=top-left, TR=top-right, BL=bottom-left, BR=bottom-right
    ; Each quadrant selects a palette (0-3).
    ;
    ; We start by writing $00 (palette 0) for all 64 bytes,
    ; then patch entries for flag and trees.
    ; -------------------------------------------------------
    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$C0
    STA PPUADDR
    LDA #$00
    LDX #$00
@clear_attr:
    STA PPUDATA
    INX
    CPX #$40
    BNE @clear_attr

    ; --- Attribute patches ---
    ; Attribute byte index = (attr_row * 8) + attr_col
    ; attr_row = tile_row / 4, attr_col = tile_col / 4
    ;
    ; Flag occupies tile rows 0-3, cols 26-29
    ;   attr_row = 0, attr_col = 6 (col 24..27) and attr_col = 7 (col 28..31)
    ;   For attr byte at (0,6): covers cols 24-27, rows 0-3
    ;     TL=col24-25,row0-1; TR=col26-27,row0-1
    ;     BL=col24-25,row2-3; BR=col26-27,row2-3
    ;     Flag is in TR and BR -> palette 1 in bits 3-2 and 7-6
    ;     Value: %10001000 = $88... but we only want TR=01, BR=01
    ;     TL=00, TR=01, BL=00, BR=01 -> %01000100 = $44
    ;   For attr byte at (0,7): covers cols 28-31, rows 0-3
    ;     TL=col28-29,row0-1; TR=col30-31,row0-1
    ;     BL=col28-29,row2-3; BR=col30-31,row2-3
    ;     Flag is in TL and BL -> palette 1
    ;     TL=01, TR=00, BL=01, BR=00 -> %00010001 = $11

    ; Patch attr (0,6): index = 0*8 + 6 = 6, PPU addr = $23C0 + 6 = $23C6
    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$C6
    STA PPUADDR
    LDA #$44
    STA PPUDATA

    ; Patch attr (0,7): index = 0*8 + 7 = 7, PPU addr = $23C7
    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$C7
    STA PPUADDR
    LDA #$11
    STA PPUDATA

    ; Trees: palette 2
    ; Tree 1 at col 5, rows 4-7
    ;   attr_row = 1 (rows 4-7), attr_col = 1 (cols 4-7)
    ;   Covers cols 4-7, rows 4-7
    ;   Tree col 5 is in the TR/BR quadrant of this attr byte
    ;   (TL=col4-5? No: each quadrant is 2x2 tiles)
    ;   Actually col 4-5 = TL/BL, col 6-7 = TR/BR
    ;   Col 5 is in the left pair (TL and BL)
    ;   TL=palette2=10, TR=00, BL=palette2=10, BR=00
    ;   %00100010 = $22
    ; attr index = 1*8+1 = 9, PPU addr = $23C0 + 9 = $23C9

    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$C9
    STA PPUADDR
    LDA #$22
    STA PPUDATA

    ; Tree 2 at col 15, rows 4-7
    ;   attr_col = 15/4 = 3, attr_row = 1
    ;   Covers cols 12-15, rows 4-7
    ;   Col 15 is in the right pair (TR/BR)
    ;   TL=00, TR=palette2=10, BL=00, BR=palette2=10
    ;   %10001000 = $88
    ; attr index = 1*8+3 = 11, PPU addr = $23C0 + 11 = $23CB

    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$CB
    STA PPUADDR
    LDA #$88
    STA PPUDATA

    ; Tree 3 at col 22, rows 4-7
    ;   attr_col = 22/4 = 5, attr_row = 1
    ;   Covers cols 20-23, rows 4-7
    ;   Col 22 is in the right pair (TR/BR): cols 22-23
    ;   TL=00, TR=palette2=10, BL=00, BR=palette2=10
    ;   %10001000 = $88
    ; attr index = 1*8+5 = 13, PPU addr = $23C0 + 13 = $23CD

    LDA PPUSTATUS
    LDA #$23
    STA PPUADDR
    LDA #$CD
    STA PPUADDR
    LDA #$88
    STA PPUDATA

    ; Ground rows 27-29: palette 0 (already $00 from clear), no patch needed

    RTS
.endproc
