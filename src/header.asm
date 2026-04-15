; iNES Header - NROM mapper (mapper 0)
.byte "NES", $1A   ; Magic bytes
.byte 2            ; 2x 16KB PRG-ROM banks (32KB total, NROM-256)
.byte 1            ; 1x 8KB CHR-ROM bank
.byte $01          ; Mapper 0, vertical mirroring
.byte $00          ; Mapper 0, no special flags
.byte $00,$00,$00,$00,$00,$00,$00,$00  ; padding
