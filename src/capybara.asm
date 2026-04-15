; capybara.asm - Capybara movement and OAM update routines

; ============================================================
; update_capybara
; Reads joypad state and updates capybara position + animation.
; Sprite is 24px wide; right boundary at $D8 to stay on screen.
; ============================================================
.proc update_capybara
    ; --- Check Right (bit 0 of joy1_buttons) ---
    LDA joy1_buttons
    AND #$01
    BEQ @check_left

    ; Move right — max X so that right edge stays on screen
    LDA capybara_x
    CMP #$D8
    BCS @check_left
    INC capybara_x

@check_left:
    ; --- Check Left (bit 1 of joy1_buttons) ---
    LDA joy1_buttons
    AND #$02
    BEQ @update_anim

    ; Move left — min X = 8
    LDA capybara_x
    CMP #$08
    BEQ @update_anim
    DEC capybara_x

@update_anim:
    ; --- Animation frame update (toggle every 8 frames) ---
    INC frame_counter
    LDA frame_counter
    CMP #$08
    BCC @done

    LDA anim_frame
    EOR #$01
    STA anim_frame

    LDA #$00
    STA frame_counter

@done:
    RTS
.endproc

; ============================================================
; update_oam
; Updates OAM buffer at $0200 with capybara sprite data.
; The capybara is a 3x3 tile (24x24 px) composite sprite.
;
; Tile layout in Pattern Table 1:
;   Frame 0 (base=$00): TL=$00 TC=$01 TR=$02
;                       ML=$03 MC=$04 MR=$05
;                       BL=$06 BC=$07 BR=$08
;   Frame 1 (base=$09): TL=$09 TC=$0A TR=$0B
;                       ML=$0C MC=$0D MR=$0E
;                       BL=$0F BC=$10 BR=$11
;
; OAM entry format: [Y, Tile#, Attr, X]
;   Row 0  Y = capybara_y
;   Row 1  Y = capybara_y + 8
;   Row 2  Y = capybara_y + 16
;   Col 0  X = capybara_x
;   Col 1  X = capybara_x + 8
;   Col 2  X = capybara_x + 16
; ============================================================
.proc update_oam
    ; --- Compute base tile and store in tile_base ZP var ---
    LDA anim_frame
    BEQ @frame0
    LDA #$09
    JMP @store_base
@frame0:
    LDA #$00
@store_base:
    STA tile_base

    ; --------------------------------------------------------
    ; Row 0 — Y = capybara_y
    ; --------------------------------------------------------

    ; OAM[0] — TL: tile = base+0
    LDA capybara_y
    STA oam_buffer + 0
    LDA tile_base       ; base+0
    STA oam_buffer + 1
    LDA #$00
    STA oam_buffer + 2
    LDA capybara_x
    STA oam_buffer + 3

    ; OAM[1] — TC: tile = base+1
    LDA capybara_y
    STA oam_buffer + 4
    LDA tile_base
    CLC
    ADC #$01
    STA oam_buffer + 5
    LDA #$00
    STA oam_buffer + 6
    LDA capybara_x
    CLC
    ADC #$08
    STA oam_buffer + 7

    ; OAM[2] — TR: tile = base+2
    LDA capybara_y
    STA oam_buffer + 8
    LDA tile_base
    CLC
    ADC #$02
    STA oam_buffer + 9
    LDA #$00
    STA oam_buffer + 10
    LDA capybara_x
    CLC
    ADC #$10
    STA oam_buffer + 11

    ; --------------------------------------------------------
    ; Row 1 — Y = capybara_y + 8
    ; --------------------------------------------------------

    ; OAM[3] — ML: tile = base+3
    LDA capybara_y
    CLC
    ADC #$08
    STA oam_buffer + 12
    LDA tile_base
    CLC
    ADC #$03
    STA oam_buffer + 13
    LDA #$00
    STA oam_buffer + 14
    LDA capybara_x
    STA oam_buffer + 15

    ; OAM[4] — MC: tile = base+4
    LDA capybara_y
    CLC
    ADC #$08
    STA oam_buffer + 16
    LDA tile_base
    CLC
    ADC #$04
    STA oam_buffer + 17
    LDA #$00
    STA oam_buffer + 18
    LDA capybara_x
    CLC
    ADC #$08
    STA oam_buffer + 19

    ; OAM[5] — MR: tile = base+5
    LDA capybara_y
    CLC
    ADC #$08
    STA oam_buffer + 20
    LDA tile_base
    CLC
    ADC #$05
    STA oam_buffer + 21
    LDA #$00
    STA oam_buffer + 22
    LDA capybara_x
    CLC
    ADC #$10
    STA oam_buffer + 23

    ; --------------------------------------------------------
    ; Row 2 — Y = capybara_y + 16
    ; --------------------------------------------------------

    ; OAM[6] — BL: tile = base+6
    LDA capybara_y
    CLC
    ADC #$10
    STA oam_buffer + 24
    LDA tile_base
    CLC
    ADC #$06
    STA oam_buffer + 25
    LDA #$00
    STA oam_buffer + 26
    LDA capybara_x
    STA oam_buffer + 27

    ; OAM[7] — BC: tile = base+7
    LDA capybara_y
    CLC
    ADC #$10
    STA oam_buffer + 28
    LDA tile_base
    CLC
    ADC #$07
    STA oam_buffer + 29
    LDA #$00
    STA oam_buffer + 30
    LDA capybara_x
    CLC
    ADC #$08
    STA oam_buffer + 31

    ; OAM[8] — BR: tile = base+8
    LDA capybara_y
    CLC
    ADC #$10
    STA oam_buffer + 32
    LDA tile_base
    CLC
    ADC #$08
    STA oam_buffer + 33
    LDA #$00
    STA oam_buffer + 34
    LDA capybara_x
    CLC
    ADC #$10
    STA oam_buffer + 35

    ; --- Hide remaining 55 sprites (entries 9-63, bytes $24-$FF) ---
    LDX #$24
@hide_loop:
    LDA #$FF
    STA oam_buffer, X   ; Y = $FF (off-screen)
    INX
    LDA #$00
    STA oam_buffer, X   ; Tile
    INX
    STA oam_buffer, X   ; Attr
    INX
    STA oam_buffer, X   ; X
    INX
    CPX #$00            ; wraps $FC→$00 after last entry
    BNE @hide_loop

    RTS
.endproc
