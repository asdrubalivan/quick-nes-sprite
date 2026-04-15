; main.asm - Quick NES Sprite: Capybara en paisaje venezolano
; Assembler: ca65 / Linker: ld65

; ============================================================
; PPU Register Addresses
; ============================================================
PPUCTRL   = $2000
PPUMASK   = $2001
PPUSTATUS = $2002
OAMADDR   = $2003
PPUSCROLL = $2005
PPUADDR   = $2006
PPUDATA   = $2007
OAMDMA    = $4014
JOY1      = $4016
JOY2      = $4017

; ============================================================
; iNES Header
; ============================================================
.segment "HEADER"
    .include "header.asm"

; ============================================================
; Zero Page Variables
; ============================================================
.segment "ZEROPAGE"
capybara_x:    .res 1   ; X position of capybara
capybara_y:    .res 1   ; Y position of capybara (fixed ~$90)
joy1_buttons:  .res 1   ; joypad 1 button state bitmask
anim_frame:    .res 1   ; animation frame (0 or 1)
frame_counter: .res 1   ; counts frames for animation timing
scroll_x:      .res 1   ; horizontal scroll value
tile_base:     .res 1   ; base tile index for current anim frame

; ============================================================
; OAM Buffer (256 bytes at $0200)
; ============================================================
.segment "OAM"
oam_buffer: .res 256

; ============================================================
; Main Code Segment
; ============================================================
.segment "CODE"

    .include "graphics.asm"
    .include "input.asm"
    .include "capybara.asm"

; ============================================================
; IRQ Handler - not used, just return
; ============================================================
IRQ:
    RTI

; ============================================================
; NMI Handler - called each VBlank
; ============================================================
NMI:
    ; Preserve registers
    PHA
    TXA
    PHA
    TYA
    PHA

    ; --- OAM DMA: copy $0200-$02FF to PPU OAM ---
    LDA #$02
    STA OAMDMA

    ; --- Read joypad ---
    JSR read_joy1

    ; --- Update capybara logic ---
    JSR update_capybara

    ; --- Update OAM buffer ---
    JSR update_oam

    ; --- Reset scroll to 0 (must be done after DMA, before frame end) ---
    LDA #$00
    STA PPUSCROLL
    STA PPUSCROLL

    ; Restore registers
    PLA
    TAY
    PLA
    TAX
    PLA

    RTI

; ============================================================
; RESET Handler - entry point after power-on or reset
; ============================================================
RESET:
    ; Disable interrupts and decimal mode
    SEI
    CLD

    ; Initialize stack pointer to $01FF
    LDX #$FF
    TXS

    ; Disable PPU rendering and NMI
    LDA #$00
    STA PPUCTRL
    STA PPUMASK

    ; -------------------------------------------------------
    ; Wait for first VBlank (PPU warm-up)
    ; -------------------------------------------------------
@wait_vblank1:
    BIT PPUSTATUS       ; read status; bit 7 = VBlank flag
    BPL @wait_vblank1   ; loop until bit 7 set

    ; -------------------------------------------------------
    ; Clear RAM $0000-$07FF (8 pages x 256 bytes)
    ; -------------------------------------------------------
    LDA #$00
    LDX #$00

    ; Page $00
@clear_page0:
    STA $0000, X
    INX
    BNE @clear_page0

    ; Page $01
@clear_page1:
    STA $0100, X
    INX
    BNE @clear_page1

    ; Page $02
@clear_page2:
    STA $0200, X
    INX
    BNE @clear_page2

    ; Page $03
@clear_page3:
    STA $0300, X
    INX
    BNE @clear_page3

    ; Page $04
@clear_page4:
    STA $0400, X
    INX
    BNE @clear_page4

    ; Page $05
@clear_page5:
    STA $0500, X
    INX
    BNE @clear_page5

    ; Page $06
@clear_page6:
    STA $0600, X
    INX
    BNE @clear_page6

    ; Page $07
@clear_page7:
    STA $0700, X
    INX
    BNE @clear_page7

    ; -------------------------------------------------------
    ; Hide all 64 sprites by setting Y = $FF in OAM buffer
    ; OAM entries are 4 bytes: [Y, Tile, Attr, X]
    ; Y byte is at offset 0, 4, 8, ..., 252
    ; -------------------------------------------------------
    LDX #$00
@hide_sprites:
    LDA #$FF
    STA oam_buffer, X   ; Y byte = $FF (off-screen)
    INX
    LDA #$00
    STA oam_buffer, X   ; Tile
    INX
    STA oam_buffer, X   ; Attr
    INX
    STA oam_buffer, X   ; X
    INX
    CPX #$00            ; X wraps from $FC to $00 after 64 sprites (256 bytes)
    BNE @hide_sprites

    ; -------------------------------------------------------
    ; Wait for second VBlank (PPU fully stable now)
    ; -------------------------------------------------------
@wait_vblank2:
    BIT PPUSTATUS
    BPL @wait_vblank2

    ; -------------------------------------------------------
    ; Initialize game variables
    ; -------------------------------------------------------
    LDA #$40
    STA capybara_x      ; start X at $40 (64 pixels from left)
    LDA #$90
    STA capybara_y      ; Y fixed at $90 (144 pixels from top)
    LDA #$00
    STA anim_frame
    STA frame_counter
    STA scroll_x
    STA joy1_buttons

    ; -------------------------------------------------------
    ; Write palettes to PPU
    ; -------------------------------------------------------
    JSR write_palettes

    ; -------------------------------------------------------
    ; Write nametable (background tilemap) to PPU
    ; -------------------------------------------------------
    JSR write_nametable

    ; -------------------------------------------------------
    ; Enable PPU:
    ;   PPUCTRL = $90: NMI enable (bit7), sprite PT=$1000 (bit3),
    ;                   BG PT=$0000 (bit4=0)
    ;   PPUMASK = $1E: show BG and sprites, no clipping
    ; -------------------------------------------------------
    LDA #$88        ; NMI enable (bit7), sprite PT=$1000 (bit3), BG PT=$0000 (bit4=0)
    STA PPUCTRL
    LDA #$1E
    STA PPUMASK

    ; Reset scroll position
    LDA #$00
    STA PPUSCROLL
    STA PPUSCROLL

    ; -------------------------------------------------------
    ; Main loop - all work done in NMI
    ; -------------------------------------------------------
@loop:
    JMP @loop

; ============================================================
; Interrupt Vectors (at $FFFA)
; ============================================================
.segment "VECTORS"
    .word NMI           ; $FFFA-$FFFB: NMI vector
    .word RESET         ; $FFFC-$FFFD: RESET vector
    .word IRQ           ; $FFFE-$FFFF: IRQ/BRK vector

; ============================================================
; CHR-ROM (8KB tile data, embebido en la ROM)
; ============================================================
.segment "CHARS"
    .incbin "../chr/sprites.chr"
