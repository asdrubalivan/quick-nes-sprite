#!/usr/bin/env python3
"""
sprite_editor.py — LLM-friendly NES sprite editor CLI para quick-nes-sprite.

Fuente de verdad: chr/capybara.spr  (texto, editado por LLM con Read/set-row)
Derivado:        chr/sprites.chr    (binario CHR-ROM 8192 bytes)

Comandos:
  init              Inicializa capybara.spr leyendo el .chr actual
  show  --tile X [--frame 0|1]
                    Muestra grid visual 8x8 + bytes derivados
  composite [--frame 0|1]
                    Muestra el sprite compuesto 24x24 en ASCII
  set-row --tile X --row R --pixels XXXXXXXX [--frame 0|1]
                    Edita una fila completa (8 chars 0-3)
  set-pixel --tile X --row R --col C --color N [--frame 0|1]
                    Edita un pixel individual
  verify            Detecta inconsistencias geométricas antes de compilar
  build             .spr -> actualiza .chr -> make clean && make
  diff              Compara capybara.spr vs sprites.chr

Colores NES (2 bits por pixel):
  0 = transparente  (plane0=0, plane1=0)
  1 = outline       (plane0=1, plane1=0)  marron oscuro
  2 = cuerpo        (plane0=0, plane1=1)  tan
  3 = oscuro        (plane0=1, plane1=1)

Bit layout dentro de cada byte: bit7 = col izquierda, bit0 = col derecha.
"""

import argparse
import pathlib
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------
ROOT     = pathlib.Path(__file__).parent.parent
CHR_PATH = ROOT / "chr" / "sprites.chr"
SPR_PATH = ROOT / "chr" / "capybara.spr"

CHR_SIZE   = 8192
TILE_SIZE  = 16
PT1_OFFSET = 4096   # Pattern Table 1 comienza en byte 4096

# ---------------------------------------------------------------------------
# Definición del sprite capybara
# ---------------------------------------------------------------------------
# Cada entrada: (nombre, indice_en_PT1, frame, comentario)
CAPYBARA_TILES = [
    # Frame 0
    ("TL", 0x00, 0, "top-left: orejas + cabeza + ojo"),
    ("TC", 0x01, 0, "top-center: cuerpo completo desde r2 — NO diagonal"),
    ("TR", 0x02, 0, "top-right: outline c16 desde r2, resto transparente"),
    ("ML", 0x03, 0, "mid-left: cuerpo + hocico"),
    ("MC", 0x04, 0, "mid-center: cuerpo taper"),
    ("MR", 0x05, 0, "mid-right: outline c16, r13+ transparente"),
    ("BL", 0x06, 0, "bottom-left: nariz + patas delanteras f0"),
    ("BC", 0x07, 0, "bottom-center: patas traseras f0"),
    ("BR", 0x08, 0, "bottom-right: vacio"),
    # Frame 1 — solo BL/BC difieren (patas desplazadas 1px)
    ("TL", 0x09, 1, "top-left f1 (idem f0)"),
    ("TC", 0x0A, 1, "top-center f1 (idem f0)"),
    ("TR", 0x0B, 1, "top-right f1 (idem f0)"),
    ("ML", 0x0C, 1, "mid-left f1 (idem f0)"),
    ("MC", 0x0D, 1, "mid-center f1 (idem f0)"),
    ("MR", 0x0E, 1, "mid-right f1 (idem f0)"),
    ("BL", 0x0F, 1, "bottom-left f1: patas shift 1px derecha"),
    ("BC", 0x10, 1, "bottom-center f1: patas traseras shift 1px"),
    ("BR", 0x11, 1, "bottom-right f1: vacio"),
]

# Layout 3x3 del sprite compuesto
COMPOSITE_ROWS = [
    ["TL", "TC", "TR"],
    ["ML", "MC", "MR"],
    ["BL", "BC", "BR"],
]

# ---------------------------------------------------------------------------
# Codificación de color ↔ planes
# ---------------------------------------------------------------------------
_COLOR_TO_PLANES = {"0": (0, 0), "1": (1, 0), "2": (0, 1), "3": (1, 1)}
_PLANES_TO_COLOR = {v: k for k, v in _COLOR_TO_PLANES.items()}


def row_str_to_bytes(row: str) -> tuple[int, int]:
    """'12222222' -> (plane0_byte, plane1_byte).  bit7=col0, bit0=col7."""
    p0 = p1 = 0
    for i, ch in enumerate(row):
        b0, b1 = _COLOR_TO_PLANES[ch]
        bit = 7 - i
        p0 |= b0 << bit
        p1 |= b1 << bit
    return p0, p1


def bytes_to_row_str(p0: int, p1: int) -> str:
    """(plane0_byte, plane1_byte) -> '12222222'."""
    return "".join(
        _PLANES_TO_COLOR[((p0 >> bit) & 1, (p1 >> bit) & 1)]
        for bit in range(7, -1, -1)
    )


def tile_rows_to_chr(rows: list[str]) -> bytes:
    """8 row strings -> 16 CHR bytes (plane0[0..7] + plane1[0..7])."""
    p0s, p1s = [], []
    for row in rows:
        p0, p1 = row_str_to_bytes(row)
        p0s.append(p0)
        p1s.append(p1)
    return bytes(p0s + p1s)


def chr_to_tile_rows(data: bytes) -> list[str]:
    """16 CHR bytes -> 8 row strings."""
    return [bytes_to_row_str(data[i], data[8 + i]) for i in range(8)]


# ---------------------------------------------------------------------------
# Clave canónica para identificar tiles
# ---------------------------------------------------------------------------
def _key(name: str, frame: int) -> str:
    return f"{name}:{frame}"


def _find_tile(name: str, frame: int):
    """Devuelve (index, comment) o None."""
    for tname, idx, tframe, comment in CAPYBARA_TILES:
        if tname == name and tframe == frame:
            return idx, comment
    return None


# ---------------------------------------------------------------------------
# I/O del archivo .spr (formato texto)
# ---------------------------------------------------------------------------

def load_spr(path: pathlib.Path) -> dict[str, list[str]]:
    """
    Lee capybara.spr y devuelve dict {"NAME:FRAME": [8 row strings]}.
    Devuelve dict vacío si el archivo no existe.
    """
    if not path.exists():
        return {}

    tiles: dict[str, list[str]] = {}
    current_key: str | None = None
    current_rows: list[str] = []

    for line in path.read_text().splitlines():
        # Strip inline comments before processing
        code = line.split("#")[0].strip()
        if not code:
            continue
        if code.startswith("[") and code.endswith("]"):
            if current_key and len(current_rows) == 8:
                tiles[current_key] = current_rows
            current_key = code[1:-1]
            current_rows = []
        elif re.fullmatch(r"[0123]{8}", code):
            current_rows.append(code)

    if current_key and len(current_rows) == 8:
        tiles[current_key] = current_rows

    return tiles


def save_spr(path: pathlib.Path, tiles: dict[str, list[str]]) -> None:
    """Escribe capybara.spr con todos los tiles del capybara."""
    lines = [
        "# capybara.spr — fuente de verdad de los tiles PT1 del capybara",
        "# Generado/editado por tools/sprite_editor.py",
        "#",
        "# Colores: 0=transparente  1=outline(marron)  2=tan(cuerpo)  3=oscuro",
        "# Paleta NES: color_1=$16  color_2=$28  color_3=$07",
        "# Bit layout: char[0]=col_izq(bit7)  char[7]=col_der(bit0)",
        "#",
        "# Para editar:",
        "#   python3 tools/sprite_editor.py set-row --tile TC --row 2 --pixels 22222222",
        "#   python3 tools/sprite_editor.py set-pixel --tile TL --row 3 --col 2 --color 3",
        "#   python3 tools/sprite_editor.py build",
        "",
    ]

    for name, idx, frame, comment in CAPYBARA_TILES:
        key = _key(name, frame)
        rows = tiles.get(key, ["00000000"] * 8)

        lines.append(f"[{key}]")
        lines.append(f"# index=$PT1:{idx:02X}  frame={frame}  {comment}")
        for r, row in enumerate(rows):
            p0, p1 = row_str_to_bytes(row)
            lines.append(f"{row}  # r{r}  plane0=0x{p0:02X} plane1=0x{p1:02X}")
        lines.append("")

    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# I/O del archivo .chr binario
# ---------------------------------------------------------------------------

def load_chr_sprites(path: pathlib.Path) -> dict[str, list[str]]:
    """Lee tiles del capybara desde .chr binario -> mismo formato que load_spr."""
    if not path.exists():
        return {}
    data = path.read_bytes()
    if len(data) != CHR_SIZE:
        return {}
    tiles: dict[str, list[str]] = {}
    for name, idx, frame, _ in CAPYBARA_TILES:
        offset = PT1_OFFSET + idx * TILE_SIZE
        tiles[_key(name, frame)] = chr_to_tile_rows(data[offset : offset + TILE_SIZE])
    return tiles


def write_chr_sprites(chr_path: pathlib.Path, tiles: dict[str, list[str]]) -> None:
    """
    Actualiza los tiles del capybara en .chr preservando los tiles de fondo (PT0).
    Si .chr no existe, crea uno de ceros.
    """
    if chr_path.exists():
        data = bytearray(chr_path.read_bytes())
        if len(data) != CHR_SIZE:
            data = bytearray(CHR_SIZE)
    else:
        data = bytearray(CHR_SIZE)

    for name, idx, frame, _ in CAPYBARA_TILES:
        key = _key(name, frame)
        rows = tiles.get(key, ["00000000"] * 8)
        offset = PT1_OFFSET + idx * TILE_SIZE
        data[offset : offset + TILE_SIZE] = tile_rows_to_chr(rows)

    chr_path.write_bytes(bytes(data))


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_init(args) -> int:
    """Inicializa capybara.spr desde el .chr actual."""
    if SPR_PATH.exists() and not getattr(args, "force", False):
        print(f"WARNING: {SPR_PATH} ya existe.")
        try:
            resp = input("¿Sobreescribir? [y/N] ").strip().lower()
        except EOFError:
            resp = ""
        if resp != "y":
            print("Cancelado. Usa --force para sobreescribir sin confirmar.")
            return 0

    tiles = load_chr_sprites(CHR_PATH)
    if not tiles:
        print(f"ERROR: No se pudo leer {CHR_PATH}")
        print("Asegúrate de ejecutar 'make' primero para generar sprites.chr")
        return 1

    save_spr(SPR_PATH, tiles)
    print(f"OK: {SPR_PATH.relative_to(ROOT)} inicializado desde {CHR_PATH.name}")
    print(f"    {len(tiles)} tiles escritos ({len(CAPYBARA_TILES)} esperados)")
    return 0


def cmd_show(args) -> int:
    """Muestra un tile con grid visual + bytes derivados."""
    name = args.tile.upper()
    frame = args.frame
    key = _key(name, frame)

    tile_info = _find_tile(name, frame)
    if tile_info is None:
        print(f"ERROR: Tile '{name}' frame {frame} no encontrado.")
        print("Tiles válidos: TL TC TR ML MC MR BL BC BR  (frame 0 o 1)")
        return 1
    idx, comment = tile_info

    tiles = load_spr(SPR_PATH)
    if not tiles:
        print(f"ERROR: {SPR_PATH.name} no existe. Ejecuta primero:")
        print(f"  python3 tools/sprite_editor.py init")
        return 1

    if key not in tiles:
        print(f"ERROR: Tile {key} no encontrado en {SPR_PATH.name}")
        return 1

    rows = tiles[key]

    print(f"tile: {name}  index: $PT1:{idx:02X}  frame: {frame}")
    print(f"comment: {comment}")
    print()
    print("     c0 c1 c2 c3 c4 c5 c6 c7")

    _VISUAL = {"0": " .", "1": " 1", "2": " 2", "3": " 3"}
    p0_list, p1_list = [], []

    for r, row in enumerate(rows):
        visual = "  ".join(_VISUAL[c] for c in row)
        p0, p1 = row_str_to_bytes(row)
        p0_list.append(f"0x{p0:02X}")
        p1_list.append(f"0x{p1:02X}")
        print(f"r{r}:  {visual}   {row}")

    print()
    print(f"plane0: [{', '.join(p0_list)}]")
    print(f"plane1: [{', '.join(p1_list)}]")
    return 0


def cmd_composite(args) -> int:
    """Muestra el sprite compuesto 24x24 en ASCII."""
    frame = args.frame

    tiles = load_spr(SPR_PATH)
    if not tiles:
        print(f"ERROR: {SPR_PATH.name} no existe. Ejecuta primero:")
        print(f"  python3 tools/sprite_editor.py init")
        return 1

    print(f"capybara frame {frame} — 3x3 tiles (24x24 px)")
    print(f"         0       8       16      24")

    global_row = 0
    for tile_row in COMPOSITE_ROWS:
        # Separador de fila de tiles
        labels = "------".join(tile_row)
        print(f"        [{labels}]")

        # Obtener los 3 tiles de esta fila
        row_tiles = [
            tiles.get(_key(tname, frame), ["00000000"] * 8)
            for tname in tile_row
        ]

        for r in range(8):
            combined = "".join(t[r] for t in row_tiles)
            visual = combined.replace("0", ".")
            print(f"r{global_row:02d}:    [{visual}]")
            global_row += 1

    return 0


def _validate_row_pixels(pixels: str) -> str | None:
    """Devuelve mensaje de error o None si es válido."""
    if not re.fullmatch(r"[0123]{8}", pixels):
        return f"debe ser exactamente 8 chars de 0-3. Recibido: {pixels!r}"
    return None


def cmd_set_row(args) -> int:
    """Edita una fila completa de un tile."""
    name = args.tile.upper()
    frame = args.frame
    row_idx = args.row
    pixels = args.pixels.strip()

    err = _validate_row_pixels(pixels)
    if err:
        print(f"ERROR: --pixels {err}")
        return 1
    if not 0 <= row_idx <= 7:
        print(f"ERROR: --row debe ser 0-7. Recibido: {row_idx}")
        return 1

    tile_info = _find_tile(name, frame)
    if tile_info is None:
        print(f"ERROR: Tile '{name}' frame {frame} no encontrado.")
        return 1

    key = _key(name, frame)
    tiles = load_spr(SPR_PATH)
    if not tiles:
        print(f"ERROR: {SPR_PATH.name} no existe. Ejecuta: sprite_editor.py init")
        return 1
    if key not in tiles:
        print(f"ERROR: Tile {key} no encontrado en {SPR_PATH.name}")
        return 1

    old_row = tiles[key][row_idx]
    tiles[key][row_idx] = pixels

    old_p0, old_p1 = row_str_to_bytes(old_row)
    new_p0, new_p1 = row_str_to_bytes(pixels)

    save_spr(SPR_PATH, tiles)

    print(f"OK: tile {name} frame {frame}, row {row_idx} actualizada")
    print(f"  antes: {old_row}  (plane0=0x{old_p0:02X}, plane1=0x{old_p1:02X})")
    print(f"  ahora: {pixels}  (plane0=0x{new_p0:02X}, plane1=0x{new_p1:02X})")
    print(f"  guardado en {SPR_PATH.name}")
    print(f"  Ejecuta 'build' para compilar a .chr y ROM.")
    return 0


def cmd_set_pixel(args) -> int:
    """Edita un pixel individual de un tile."""
    name = args.tile.upper()
    frame = args.frame
    row_idx = args.row
    col_idx = args.col
    color = str(args.color)

    if not 0 <= row_idx <= 7:
        print(f"ERROR: --row debe ser 0-7.")
        return 1
    if not 0 <= col_idx <= 7:
        print(f"ERROR: --col debe ser 0-7.")
        return 1

    tile_info = _find_tile(name, frame)
    if tile_info is None:
        print(f"ERROR: Tile '{name}' frame {frame} no encontrado.")
        return 1

    key = _key(name, frame)
    tiles = load_spr(SPR_PATH)
    if not tiles:
        print(f"ERROR: {SPR_PATH.name} no existe. Ejecuta: sprite_editor.py init")
        return 1
    if key not in tiles:
        print(f"ERROR: Tile {key} no encontrado en {SPR_PATH.name}")
        return 1

    old_row = tiles[key][row_idx]
    old_color = old_row[col_idx]
    new_row = old_row[:col_idx] + color + old_row[col_idx + 1 :]
    tiles[key][row_idx] = new_row

    old_p0, old_p1 = row_str_to_bytes(old_row)
    new_p0, new_p1 = row_str_to_bytes(new_row)

    save_spr(SPR_PATH, tiles)

    print(f"OK: tile {name} frame {frame}, r{row_idx} c{col_idx}: {old_color} -> {color}")
    print(f"  row antes: {old_row}  (plane0=0x{old_p0:02X}, plane1=0x{old_p1:02X})")
    print(f"  row ahora: {new_row}  (plane0=0x{new_p0:02X}, plane1=0x{new_p1:02X})")
    print(f"  guardado en {SPR_PATH.name}")
    print(f"  Ejecuta 'build' para compilar a .chr y ROM.")
    return 0


def cmd_verify(args) -> int:
    """Detecta inconsistencias geométricas en el sprite compuesto."""
    del args  # no usado; requerido por la tabla de dispatch
    tiles = load_spr(SPR_PATH)
    if not tiles:
        print(f"ERROR: {SPR_PATH.name} no existe.")
        return 1

    warnings = []
    errors = []

    for frame in [0, 1]:
        # Construir grid 24x24 de colores
        grid: list[str] = []
        for tile_row in COMPOSITE_ROWS:
            row_tiles = [
                tiles.get(_key(tname, frame), ["00000000"] * 8)
                for tname in tile_row
            ]
            for r in range(8):
                grid.append("".join(t[r] for t in row_tiles))

        # --- Check 1: TC rows 2-7 no deben ser transparentes ---
        tc_key = _key("TC", frame)
        tc_rows = tiles.get(tc_key, ["00000000"] * 8)
        for r in range(2, 8):
            if tc_rows[r] == "00000000":
                errors.append(
                    f"frame {frame}: TC r{r} es transparente — "
                    f"cuerpo crece en diagonal (BUG del triángulo). "
                    f"Debe ser '22222222'."
                )

        # --- Check 2: MC rows 0-4 no deben ser transparentes ---
        mc_key = _key("MC", frame)
        mc_rows = tiles.get(mc_key, ["00000000"] * 8)
        for r in range(0, 5):
            if mc_rows[r] == "00000000":
                errors.append(
                    f"frame {frame}: MC r{r} es transparente — "
                    f"cuerpo central vacío. Debe tener color 2 (tan)."
                )

        # --- Check 3: TR / MR no deben tener píxeles en col 1-7 ---
        for tname in ("TR", "MR"):
            t_key = _key(tname, frame)
            t_rows = tiles.get(t_key, ["00000000"] * 8)
            for r, row in enumerate(t_rows):
                if any(c != "0" for c in row[1:]):
                    warnings.append(
                        f"frame {frame}: {tname} r{r} tiene pixeles en col 1-7 "
                        f"(solo col0=outline esperado): {row}"
                    )

        # --- Check 4: ancho del cuerpo consistente filas 2-15 ---
        body_rows = grid[2:16]
        widths = []
        for row in body_rows:
            rightmost = -1
            for c in range(23, -1, -1):
                if row[c] != "0":
                    rightmost = c
                    break
            widths.append(rightmost)

        for i in range(1, len(widths)):
            if widths[i] >= 0 and widths[i - 1] >= 0:
                delta = widths[i - 1] - widths[i]
                if delta > 3:
                    warnings.append(
                        f"frame {frame}: ancho cae bruscamente en r{i+2} "
                        f"(r{i+1}=c{widths[i-1]}, r{i+2}=c{widths[i]}) — "
                        f"posible cuña diagonal"
                    )

    total_err = len(errors)
    total_warn = len(warnings)

    if errors:
        print(f"ERRORES ({total_err}):")
        for e in errors:
            print(f"  ERROR: {e}")
        print()

    if warnings:
        print(f"WARNINGS ({total_warn}):")
        for w in warnings:
            print(f"  WARN: {w}")
        print()

    if total_err == 0 and total_warn == 0:
        print(f"OK: {len(tiles)} tiles, 0 errores, 0 warnings.")
        print("Sprite geométricamente consistente. Listo para build.")
    else:
        print(f"Resumen: {total_err} errores, {total_warn} warnings en {len(tiles)} tiles.")

    return 1 if errors else 0


def cmd_build(args) -> int:
    """Genera .chr desde .spr y compila la ROM."""
    del args  # no usado; requerido por la tabla de dispatch
    tiles = load_spr(SPR_PATH)
    if not tiles:
        print(f"ERROR: {SPR_PATH.name} no existe. Ejecuta: sprite_editor.py init")
        return 1

    print(f"[1/3] Parseando {SPR_PATH.name} ... {len(tiles)} tiles OK")

    write_chr_sprites(CHR_PATH, tiles)
    print(f"[2/3] Actualizando {CHR_PATH.name} ... {CHR_PATH.stat().st_size} bytes")

    print(f"[3/3] Ejecutando make clean && make ...")
    result = subprocess.run(
        "make clean && make",
        shell=True,
        cwd=ROOT,
    )

    if result.returncode == 0:
        nes_path = ROOT / "game.nes"
        nes_size = nes_path.stat().st_size if nes_path.exists() else 0
        print(f"\nBUILD OK: game.nes ({nes_size} bytes)")
        print("Para ejecutar en FCEUX: make run")
    else:
        print(f"\nBUILD FAILED (returncode={result.returncode})")
        return 1

    return 0


def cmd_diff(args) -> int:
    """Compara capybara.spr vs sprites.chr tile por tile."""
    del args  # no usado; requerido por la tabla de dispatch
    spr_tiles = load_spr(SPR_PATH)
    chr_tiles = load_chr_sprites(CHR_PATH)

    if not spr_tiles:
        print(f"ERROR: {SPR_PATH.name} no existe.")
        return 1
    if not chr_tiles:
        print(f"ERROR: {CHR_PATH.name} no existe o es inválido.")
        return 1

    print(f"Comparando {SPR_PATH.name} vs {CHR_PATH.name} ...")
    print()

    diffs = 0
    matches = 0

    for name, _, frame, _ in CAPYBARA_TILES:
        key = _key(name, frame)
        spr_rows = spr_tiles.get(key)
        chr_rows = chr_tiles.get(key)

        if spr_rows == chr_rows:
            matches += 1
            print(f"  {key:6}: MATCH")
        else:
            diffs += 1
            print(f"  {key:6}: DIFFERS")
            if spr_rows and chr_rows:
                for r in range(8):
                    if spr_rows[r] != chr_rows[r]:
                        print(f"    r{r}: .spr={spr_rows[r]}  .chr={chr_rows[r]}")

    print()
    if diffs == 0:
        print(f"Resultado: {matches}/{matches} tiles en sync (.spr == .chr).")
    else:
        print(f"Resultado: {matches} en sync, {diffs} difieren.")
        print("Hint: ejecuta 'build' para sincronizar .chr desde .spr.")

    return 0


# ---------------------------------------------------------------------------
# CLI principal
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sprite_editor.py",
        description="LLM-friendly NES sprite editor para quick-nes-sprite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Inicializa capybara.spr desde sprites.chr")
    p_init.add_argument("--force", action="store_true", help="Sobreescribir sin confirmar")

    # show
    p_show = sub.add_parser("show", help="Muestra un tile con grid visual + bytes")
    p_show.add_argument("--tile", required=True,
                        help="Nombre: TL TC TR ML MC MR BL BC BR")
    p_show.add_argument("--frame", type=int, default=0, choices=[0, 1])

    # composite
    p_comp = sub.add_parser("composite", help="Sprite compuesto 24x24 en ASCII")
    p_comp.add_argument("--frame", type=int, default=0, choices=[0, 1])

    # set-row
    p_sr = sub.add_parser("set-row", help="Edita una fila completa del tile")
    p_sr.add_argument("--tile", required=True)
    p_sr.add_argument("--row", type=int, required=True, help="Fila 0-7")
    p_sr.add_argument("--pixels", required=True,
                      help="8 chars de 0-3 ej: 22222222")
    p_sr.add_argument("--frame", type=int, default=0, choices=[0, 1])

    # set-pixel
    p_sp = sub.add_parser("set-pixel", help="Edita un pixel individual")
    p_sp.add_argument("--tile", required=True)
    p_sp.add_argument("--row", type=int, required=True, help="Fila 0-7")
    p_sp.add_argument("--col", type=int, required=True, help="Columna 0-7")
    p_sp.add_argument("--color", type=int, required=True, choices=[0, 1, 2, 3])
    p_sp.add_argument("--frame", type=int, default=0, choices=[0, 1])

    # verify
    sub.add_parser("verify", help="Detecta inconsistencias geométricas")

    # build
    sub.add_parser("build", help=".spr -> .chr -> make clean && make")

    # diff
    sub.add_parser("diff", help="Compara capybara.spr vs sprites.chr")

    args = parser.parse_args()

    dispatch = {
        "init":      cmd_init,
        "show":      cmd_show,
        "composite": cmd_composite,
        "set-row":   cmd_set_row,
        "set-pixel": cmd_set_pixel,
        "verify":    cmd_verify,
        "build":     cmd_build,
        "diff":      cmd_diff,
    }

    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
