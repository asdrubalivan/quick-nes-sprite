# quick-nes-sprite

A NES game featuring an animated capybara in a Venezuelan landscape, built with ca65/ld65 and a custom LLM-friendly sprite editor.

## Demo

The capybara is a 24×24 pixel composite sprite (3×3 tiles) with a 2-frame walking animation. Move it left and right with the D-pad.

```
r00:    [..11.11.................]
r01:    [.1221221................]
r02:    [12222222222222221.......]
r03:    [12122222222222221.......]   ← eye at col 2
r08:    [12222222222222221.......]
r13:    [112222222222221.........]   ← snout
r17:    [...12.12.12.12..........]  ← legs (frame 0)
```

## Requirements

```bash
brew install cc65 fceux
```

- `cc65` — ca65 assembler + ld65 linker
- `fceux` — NES emulator

## Build & Run

```bash
make        # assemble and link → game.nes
make run    # open in FCEUX
make clean  # remove build artifacts
```

## Project Structure

```
quick-nes-sprite/
├── src/
│   ├── main.asm        # RESET/NMI handlers, ZP variables
│   ├── header.asm      # iNES header (NROM-256, mapper 0)
│   ├── graphics.asm    # write_palettes, write_nametable
│   ├── input.asm       # read_joy1 — joypad reading
│   └── capybara.asm    # update_capybara, update_oam
├── chr/
│   ├── capybara.spr    # Sprite pixel data (text, source of truth)
│   └── sprites.chr     # CHR-ROM binary (8192 bytes, derived)
├── tools/
│   ├── sprite_editor.py  # LLM-friendly sprite editor CLI
│   └── gen_chr.py        # Full CHR-ROM generator (background tiles)
├── game.cfg            # ld65 linker config
└── Makefile
```

## Sprite Editor

Editing NES sprites by hand-calculating `plane0`/`plane1` bytes is error-prone. `sprite_editor.py` lets you work in terms of pixel colors (0–3) instead of raw bits.

### Format (`chr/capybara.spr`)

Each tile is described as 8 rows of 8 characters. Each character is the pixel color; position is the column.

```
[TC:0]
# top-center: full-width body from row 2
00000000  # r0 — transparent (ears are in TL)
00000000  # r1
22222222  # r2 — tan body fill, full width
22222222  # r3-r7
```

Colors: `0`=transparent `1`=outline `2`=tan body `3`=dark

### CLI Commands

```bash
# Initialize from current .chr
python3 tools/sprite_editor.py init

# Inspect a tile
python3 tools/sprite_editor.py show --tile TC
python3 tools/sprite_editor.py show --tile BL --frame 1

# View the full 24×24 composite in ASCII
python3 tools/sprite_editor.py composite --frame 0

# Edit
python3 tools/sprite_editor.py set-row   --tile TC --row 2 --pixels 22222222
python3 tools/sprite_editor.py set-pixel --tile TL --row 3 --col 2 --color 3

# Check for geometric errors before building
python3 tools/sprite_editor.py verify

# Compile: .spr → .chr → make clean && make
python3 tools/sprite_editor.py build

# Check sync between .spr and .chr
python3 tools/sprite_editor.py diff
```

`verify` automatically detects the **diagonal-body bug**: if the center tile `TC` has transparent rows where the body should be full-width, the composite silhouette appears as a triangle instead of an oval.

## NES Technical Notes

- **Mapper**: NROM-256 (mapper 0) — 32 KB PRG-ROM + 8 KB CHR-ROM
- **Pattern Table 0** (`$0000–$0FFF`): background tiles (sky, grass, tree, flag)
- **Pattern Table 1** (`$1000–$1FFF`): capybara sprite tiles (frames 0 and 1)
- **PPUCTRL**: `$88` — NMI enable (bit 7) + sprite PT at `$1000` (bit 3)
- **OAM buffer**: `$0200–$02FF`, transferred via DMA each NMI

### Tile Layout (PT1)

```
Frame 0 (base=$00):  TL=$00  TC=$01  TR=$02
                     ML=$03  MC=$04  MR=$05
                     BL=$06  BC=$07  BR=$08

Frame 1 (base=$09):  TL–MR identical to frame 0
                     BL=$0F  BC=$10  BR=$11  ← animated legs
```

### Color Encoding

| Color | plane0 bit | plane1 bit | Meaning    |
|-------|-----------|-----------|------------|
| 0     | 0         | 0         | Transparent |
| 1     | 1         | 0         | Dark outline |
| 2     | 0         | 1         | Tan body fill |
| 3     | 1         | 1         | Darkest |

Within each byte: **bit 7 = leftmost column, bit 0 = rightmost**.

## License

MIT
