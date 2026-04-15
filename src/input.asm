; input.asm - Joypad reading routines

; ============================================================
; read_joy1
; Reads 8 buttons from joypad 1 into joy1_buttons.
; Button bit layout in joy1_buttons (after this routine):
;   bit 7 = A
;   bit 6 = B
;   bit 5 = Select
;   bit 4 = Start
;   bit 3 = Up
;   bit 2 = Down
;   bit 1 = Left
;   bit 0 = Right
; ============================================================
.proc read_joy1
    ; Strobe the joypad (latch current button state)
    LDA #$01
    STA JOY1
    LDA #$00
    STA JOY1

    ; Read 8 bits. Each read of $4016 returns one bit in bit 0.
    ; We use ROL to shift bits into A from the right side.
    ; After 8 reads + ROLs the buttons fill A:
    ;   First read (A button) ends up in bit 7.

    LDA #$00
    STA joy1_buttons

    ; Read button A
    LDA JOY1
    LSR A               ; bit 0 -> carry
    ROL joy1_buttons    ; carry -> bit 0 of joy1_buttons, shift left

    ; Read button B
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; Read Select
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; Read Start
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; Read Up
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; Read Down
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; Read Left
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; Read Right
    LDA JOY1
    LSR A
    ROL joy1_buttons

    ; joy1_buttons now contains:
    ;   bit 7 = A (first read, shifted left 7 times)
    ;   bit 6 = B
    ;   bit 5 = Select
    ;   bit 4 = Start
    ;   bit 3 = Up
    ;   bit 2 = Down
    ;   bit 1 = Left
    ;   bit 0 = Right

    RTS
.endproc
