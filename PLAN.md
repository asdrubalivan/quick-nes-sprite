# Plan: Juego NES - Capybara en Paisaje Venezolano

## Concepto
Un juego NES donde un capybara se mueve horizontalmente en un paisaje lateral con árboles y una bandera de Venezuela al fondo.

---

## Stack de herramientas

| Herramienta | Propósito |
|---|---|
| **ca65** (parte de cc65) | Ensamblador 6502 para macOS |
| **ld65** | Linker (también parte de cc65) |
| **Mesen** o **FCEUX** | Emulador NES con soporte para depuración |
| **make** | Build automation |
| **Python 3** | Utilidad de conteo de ciclos CPU (idea del usuario) |

### Instalación en macOS
```bash
brew install cc65
# Mesen: descargar desde https://mesen.ca (requiere .NET)
# Alternativa: FCEUX via brew o binario
```

---

## Arquitectura del ROM NES

### Estructura del archivo .nes (formato iNES)
```
[Header 16 bytes]  - Identificador "NES\x1A", tamaño PRG/CHR
[PRG-ROM 16KB]     - Código 6502 (lógica del juego)
[CHR-ROM 8KB]      - Datos gráficos (tiles 8x8 píxeles)
```

### Mapeador
**NROM (Mapper 0)** — el más simple, sin bankswitching. Suficiente para este proyecto.

---

## Gráficos planeados

### Sistema de paletas NES
- Fondo: 4 paletas × 4 colores (color 0 = transparente/fondo compartido)
- Sprites: 4 paletas × 4 colores
- Total simultáneo en pantalla: 25 colores

### Tiles necesarios (CHR-ROM, cada tile = 8x8px, 16 bytes)

#### Sprites del capybara (OAM, 8x8 o 8x16)
- Capybara cuerpo izquierda / derecha (flip horizontal)
- Patas animadas (2 frames)

#### Tiles de fondo (Nametable)
- Suelo (hierba)
- Tronco de árbol
- Copa de árbol (2-3 variaciones)
- Cielo (tile vacío)

#### Bandera de Venezuela (en el fondo, tiles de nametable)
La bandera tiene 3 franjas horizontales:
- **Amarillo** (mitad superior)
- **Azul** (centro)
- **Rojo** (inferior)
- 8 estrellas blancas en arco (simplificadas como puntos en el tile)
- Se dibuja como un rectángulo de ~4x6 tiles en la nametable

---

## Estructura de archivos del proyecto

```
quick-nes-sprite/
├── Makefile
├── src/
│   ├── main.asm        ← Punto de entrada, vectores IRQ/NMI/RESET
│   ├── header.asm      ← Header iNES
│   ├── graphics.asm    ← Rutinas PPU (escritura nametable, OAM)
│   ├── input.asm       ← Lectura del controlador
│   └── capybara.asm    ← Lógica de movimiento del capybara
├── chr/
│   └── sprites.chr     ← Datos de tiles (generado o hecho a mano)
├── tools/
│   └── cycle_counter.py ← Utilidad Python para contar ciclos CPU
└── game.nes            ← ROM compilada (output)
```

---

## Flujo del juego (game loop)

```
RESET → Inicializar PPU, RAM, paletas
      → Cargar nametable (fondo: cielo, suelo, árboles, bandera)
      → Configurar OAM con capybara en posición inicial
      → Habilitar NMI

NMI (VBlank) → Copiar OAM via DMA ($4014)
             → Leer controlador ($4016/$4017)
             → Actualizar posición X del capybara
             → Animar frame de patas
             → Scroll opcional del fondo
```

---

## Lógica de movimiento

```asm
; En NMI handler, después de DMA:
LDA joy1_buttons
AND #%00000010    ; botón Right (D-pad)
BEQ .check_left
  INC capybara_x
.check_left:
LDA joy1_buttons
AND #%00000100    ; botón Left
BEQ .done
  DEC capybara_x
.done:
```

Límites: X entre $08 y $F0 para no salir de pantalla.

---

## Utilidad Python: contador de ciclos

Idea: un script que parsea el output del ensamblado y suma ciclos de instrucciones 6502 para un segmento dado.

```python
# tools/cycle_counter.py
# Uso: python3 cycle_counter.py src/capybara.asm
# Output: tabla de instrucciones con ciclos por instrucción y total
```

Ciclos útiles a vigilar:
- NMI handler debe completarse en < ~2274 ciclos (tiempo de VBlank)
- Lectura de controlador: 8 × LDA+AND+BEQ ≈ ~56 ciclos

---

## Próximos pasos concretos

1. `src/header.asm` — Header iNES 16 bytes
2. `src/main.asm` — RESET handler, NMI handler, vectores
3. `chr/sprites.chr` — Datos CHR con tiles del capybara y fondo
4. `src/graphics.asm` — Rutina de escritura de paletas y nametable
5. `src/input.asm` — Lectura del joypad
6. `src/capybara.asm` — Movimiento y animación
7. `Makefile` — `ca65 + ld65` pipeline
8. `tools/cycle_counter.py` — Analizador de ciclos

---

## Referencias
- [NESdev Wiki](https://www.nesdev.org/wiki/)
- [cc65 docs](https://cc65.github.io/doc/ca65.html)
- [nes-starter-kit](https://github.com/cppchriscpp/nes-starter-kit)
- [Pikuma NES course](https://pikuma.com/courses/nes-game-programming-tutorial)
