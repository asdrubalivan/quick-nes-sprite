# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`quick-nes-sprite` is a greenfield project. This CLAUDE.md will be expanded as the codebase grows.

**Domain context**: NES (Nintendo Entertainment System) sprites. NES graphics use a tile-based system with 8×8 pixel tiles, a 2-bit-per-pixel color model (4 colors per palette, up to 8 background palettes + 4 sprite palettes), CHR ROM/RAM for tile data stored in a custom binary format, and OAM (Object Attribute Memory) for sprite position/attributes.

## Build system

```bash
make          # compila y linkea → game.nes
make clean    # borra build/ y game.nes
make run      # abre game.nes en fceux
```

Herramientas requeridas: `cc65` (ca65 + ld65), `fceux` — instalar con `brew install cc65 fceux`.

## Arquitectura

| Archivo | Rol |
|---|---|
| `src/main.asm` | Entrada RESET/NMI, variables ZP, incluye los demás |
| `src/header.asm` | Header iNES 16 bytes |
| `src/graphics.asm` | `write_palettes`, `write_nametable` |
| `src/input.asm` | `read_joy1` — bitmask en `joy1_buttons` |
| `src/capybara.asm` | `update_capybara`, `update_oam` |
| `chr/capybara.spr` | **Fuente de verdad** de los 18 tiles del capybara (texto, editado por LLM) |
| `chr/sprites.chr` | CHR-ROM binario de 8192 bytes (derivado de capybara.spr + gen_chr.py) |
| `tools/sprite_editor.py` | CLI LLM-friendly para editar tiles sin calcular bytes manualmente |
| `game.cfg` | Configuración del linker ld65 |

**Mapper**: NROM-256 (mapper 0) — 2 bancos PRG (32KB) + 1 banco CHR (8KB).

## Constantes críticas

- `PPUCTRL = $88` — NMI enable (bit 7) + sprite PT en $1000 (bit 3) + BG PT en $0000 (bit 4=0). **No usar $90** (invierte las tablas de patrones).
- OAM buffer en `$0200–$02FF`. OAM DMA: `LDA #$02 / STA $4014`.
- Pattern table 0 (`$0000–$0FFF`): tiles de fondo (cielo, hierba, árbol, bandera).
- Pattern table 1 (`$1000–$1FFF`): tiles del capybara (frames 0 y 1).

## Variables zero page

| Símbolo | Dirección | Uso |
|---|---|---|
| `capybara_x` | `$00` | X del capybara |
| `capybara_y` | `$01` | Y del capybara (fijo ~$90) |
| `joy1_buttons` | `$02` | Bitmask joypad 1 (bit0=Right, bit1=Left) |
| `anim_frame` | `$03` | Frame animación (0 o 1) |
| `frame_counter` | `$04` | Contador para temporizar animación |
| `scroll_x` | `$05` | Scroll horizontal |
| `tile_base` | `$06` | Tile base del frame actual (0 o 9), temp de update_oam |

## CHR tile layout

**PT0 (fondo)**: $00=cielo, $01=hierba, $02=tronco árbol, $03=follaje, $04=amarillo bandera, $05=azul bandera, $06=rojo bandera.

**PT1 (sprites)**: capybara 3×3 tiles (24×24 px), 2 frames de animación.

```
Frame 0 (base=$00):  TL=$00  TC=$01  TR=$02
                     ML=$03  MC=$04  MR=$05
                     BL=$06  BC=$07  BR=$08

Frame 1 (base=$09):  TL=$09  TC=$0A  TR=$0B  (idénticos a frame 0)
                     ML=$0C  MC=$0D  MR=$0E  (idénticos a frame 0)
                     BL=$0F  BC=$10  BR=$11  (patas animadas)
```

Para regenerar CHR desde cero: `python3 tools/gen_chr.py` → sobreescribe `chr/sprites.chr`.  
**Importante**: `make` no detecta cambios en `chr/sprites.chr` automáticamente. Usar `make clean && make` después de regenerar el CHR.

**Preferido para edición de sprites**: usar `tools/sprite_editor.py` (ver sección abajo).

## Sprites compuestos NES — reglas de diseño

### Codificación de color en tiles
- `plane0[row]`: bit = 1 donde el pixel es **color 1** (marrón oscuro/outline)
- `plane1[row]`: bit = 1 donde el pixel es **color 2** (tan/body fill)
- Dentro de cada byte: **bit 7 = columna izquierda del tile**, bit 0 = columna derecha
- Color 0 (transparente): plane0=0, plane1=0
- Color 3: plane0=1, plane1=1

### Regla crítica — ancho constante del cuerpo
El cuerpo debe tener **ancho completo desde la primera fila visible**, no crecer en diagonal.  
Si un tile central (TC, MC) es transparente en las primeras filas, la silueta aparece como **triángulo/cuña** en lugar de oval.

**Patrón correcto** para un tile de cuerpo central:
```python
# TC (cols 8-15): transparente en filas de orejas, tan completo en cuerpo
plane0=[0x00]*8        # sin color-1
plane1=[0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]  # tan desde fila 2
```

**Patrón correcto** para el tile de borde derecho:
```python
# TR / MR: solo outline en c16 (bit7), resto transparente
plane0=[0x00, 0x00, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80]
plane1=[0x00]*8
```

### OAM update — patrón con tile_base
Para sprites de múltiples tiles, almacenar el tile base en ZP y sumar offset para cada entry:
```asm
LDA anim_frame
BEQ @f0
LDA #$09        ; frame 1 base
JMP @store
@f0:
LDA #$00        ; frame 0 base
@store:
STA tile_base

; Para cada OAM entry:
LDA tile_base
CLC
ADC #offset     ; 0..8 para grid 3×3
STA oam_buffer + (entry*4+1)
```

### Límites de movimiento con sprite compuesto
- Sprite 24px de ancho → límite derecho: `CMP #$D8` (deja margen hasta $FF)
- Sprite 24px de alto → capybara_y=$90 → bottom a $A8 (sobre el suelo en ~$D8)

## Sprite editor LLM-friendly

### Formato `chr/capybara.spr` — fuente de verdad

Cada tile se describe con 8 strings de 8 caracteres. Cada carácter es el color del pixel; la posición es la columna (char[0]=col izquierda, char[7]=col derecha). **No requiere aritmética de bits.**

```
[TC:0]
# index=$PT1:01  frame=0  top-center: cuerpo completo desde r2
00000000  # r0
00000000  # r1
22222222  # r2  ← tan completo, NO empieza en diagonal
22222222  # r3-r7
...
```

Colores: `0`=transparente `1`=outline(marrón) `2`=tan(cuerpo) `3`=oscuro.  
El LLM puede leer este archivo directamente con la herramienta `Read`.

### Workflow de edición LLM-driven

```bash
# 1. Primera vez: inicializar .spr desde el .chr actual
python3 tools/sprite_editor.py init

# 2. Ver estado actual de un tile
python3 tools/sprite_editor.py show --tile TC
python3 tools/sprite_editor.py show --tile TL --frame 1

# 3. Ver el sprite compuesto 24x24 completo
python3 tools/sprite_editor.py composite --frame 0

# 4. Editar una fila completa
python3 tools/sprite_editor.py set-row --tile TC --row 2 --pixels 22222222

# 5. Editar un pixel individual
python3 tools/sprite_editor.py set-pixel --tile TL --row 3 --col 2 --color 3

# 6. Verificar consistencia geométrica ANTES de compilar
python3 tools/sprite_editor.py verify

# 7. Compilar: .spr → .chr → make clean && make
python3 tools/sprite_editor.py build

# 8. Comparar .spr vs .chr en disco
python3 tools/sprite_editor.py diff
```

### Comandos disponibles

| Comando | Descripción |
|---|---|
| `init [--force]` | Inicializa `capybara.spr` desde `sprites.chr` |
| `show --tile X [--frame 0\|1]` | Grid visual 8×8 + bytes plane0/plane1 derivados |
| `composite [--frame 0\|1]` | Sprite compuesto 24×24 en ASCII — útil para detectar cuñas diagonales |
| `set-row --tile X --row R --pixels XXXXXXXX` | Edita una fila completa (8 chars 0-3) |
| `set-pixel --tile X --row R --col C --color N` | Edita un pixel |
| `verify` | Detecta TC/MC transparentes, TR/MR con pixels fuera de col 0, cuerpo diagonal |
| `build` | `.spr` → actualiza `.chr` → `make clean && make` |
| `diff` | Muestra qué tiles difieren entre `.spr` y `.chr` |

### Tiles válidos para `--tile`

`TL` `TC` `TR` `ML` `MC` `MR` `BL` `BC` `BR` — con `--frame 0` (default) o `--frame 1`.

### Relación con gen_chr.py

- `gen_chr.py` gestiona los tiles de **fondo** (PT0) y puede regenerar el CHR completo desde cero.
- `sprite_editor.py build` actualiza **solo los 18 tiles del capybara** (PT1) en el `.chr`, preservando los tiles de fondo.
- Si se ejecuta `python3 tools/gen_chr.py`, usar `python3 tools/sprite_editor.py build` a continuación para re-aplicar el `.spr`.

### Invariante crítica del composite (checker `verify`)

El comando `verify` detecta automáticamente el **bug del triángulo**:
- `TC` rows 2-7 deben ser `22222222` (no transparentes)
- `MC` rows 0-4 deben tener color 2 (no transparentes)
- `TR` y `MR` no deben tener pixels en cols 1-7 (solo outline en col 0)
- El ancho del cuerpo no debe caer más de 3px entre filas consecutivas
