#!/usr/bin/env python3
"""
cycle_counter.py - Analizador de ciclos de CPU 6502 para ca65.

Uso: python3 cycle_counter.py src/capybara.asm
"""

import sys
import re

CYCLES = {
    ('ADC', 'imm'): 2, ('ADC', 'zp'): 3, ('ADC', 'abs'): 4,
    ('AND', 'imm'): 2, ('AND', 'zp'): 3, ('AND', 'abs'): 4,
    ('ASL', 'acc'): 2, ('ASL', 'zp'): 5, ('ASL', 'abs'): 6,
    ('BCC', 'rel'): 2, ('BCS', 'rel'): 2,
    ('BEQ', 'rel'): 2, ('BNE', 'rel'): 2,
    ('BMI', 'rel'): 2, ('BPL', 'rel'): 2,
    ('BVC', 'rel'): 2, ('BVS', 'rel'): 2,
    ('BIT', 'zp'): 3, ('BIT', 'abs'): 4,
    ('BRK', 'imp'): 7,
    ('CLC', 'imp'): 2, ('CLD', 'imp'): 2,
    ('CLI', 'imp'): 2, ('CLV', 'imp'): 2,
    ('CMP', 'imm'): 2, ('CMP', 'zp'): 3, ('CMP', 'abs'): 4,
    ('CPX', 'imm'): 2, ('CPX', 'zp'): 3, ('CPX', 'abs'): 4,
    ('CPY', 'imm'): 2, ('CPY', 'zp'): 3, ('CPY', 'abs'): 4,
    ('DEC', 'zp'): 5, ('DEC', 'abs'): 6,
    ('DEX', 'imp'): 2, ('DEY', 'imp'): 2,
    ('EOR', 'imm'): 2, ('EOR', 'zp'): 3, ('EOR', 'abs'): 4,
    ('INC', 'zp'): 5, ('INC', 'abs'): 6,
    ('INX', 'imp'): 2, ('INY', 'imp'): 2,
    ('JMP', 'abs'): 3, ('JMP', 'ind'): 5,
    ('JSR', 'abs'): 6,
    ('LDA', 'imm'): 2, ('LDA', 'zp'): 3, ('LDA', 'abs'): 4,
    ('LDA', 'abs,x'): 4, ('LDA', 'abs,y'): 4,
    ('LDA', '(ind),y'): 5, ('LDA', 'zp,x'): 4,
    ('LDX', 'imm'): 2, ('LDX', 'zp'): 3, ('LDX', 'abs'): 4,
    ('LDY', 'imm'): 2, ('LDY', 'zp'): 3, ('LDY', 'abs'): 4,
    ('LSR', 'acc'): 2, ('LSR', 'zp'): 5,
    ('NOP', 'imp'): 2,
    ('ORA', 'imm'): 2, ('ORA', 'zp'): 3, ('ORA', 'abs'): 4,
    ('PHA', 'imp'): 3, ('PHP', 'imp'): 3,
    ('PLA', 'imp'): 4, ('PLP', 'imp'): 4,
    ('ROL', 'acc'): 2, ('ROL', 'zp'): 5,
    ('ROR', 'acc'): 2, ('ROR', 'zp'): 5,
    ('RTI', 'imp'): 6, ('RTS', 'imp'): 6,
    ('SBC', 'imm'): 2, ('SBC', 'zp'): 3, ('SBC', 'abs'): 4,
    ('SEC', 'imp'): 2, ('SED', 'imp'): 2, ('SEI', 'imp'): 2,
    ('STA', 'zp'): 3, ('STA', 'abs'): 4, ('STA', 'abs,x'): 5,
    ('STA', 'abs,y'): 5, ('STA', '(ind),y'): 6,
    ('STX', 'zp'): 3, ('STX', 'abs'): 4,
    ('STY', 'zp'): 3, ('STY', 'abs'): 4,
    ('TAX', 'imp'): 2, ('TAY', 'imp'): 2,
    ('TSX', 'imp'): 2, ('TXA', 'imp'): 2,
    ('TXS', 'imp'): 2, ('TYA', 'imp'): 2,
}

BRANCH_MNEMONICS = {'BEQ', 'BNE', 'BCC', 'BCS', 'BPL', 'BMI', 'BVC', 'BVS'}

VBLANK_CYCLE_BUDGET = 2274


def detect_mode(mnemonic: str, operand: str) -> str:
    """Determina el modo de direccionamiento a partir del operando."""
    operand = operand.strip()

    # Instrucciones branch siempre usan modo relativo
    if mnemonic in BRANCH_MNEMONICS:
        return 'rel'

    # Sin operando → implied
    if not operand:
        return 'imp'

    # Acumulador explícito
    if operand.upper() == 'A':
        return 'acc'

    # Inmediato: #$XX o #%XXXXX o #numero
    if operand.startswith('#'):
        return 'imm'

    # Indirecto indexado: ($XX),Y
    if re.match(r'^\(\$[0-9A-Fa-f]{2}\)\s*,\s*[Yy]$', operand):
        return '(ind),y'

    # Indirecto (JMP): ($XXXX)
    if re.match(r'^\(\$[0-9A-Fa-f]{4}\)$', operand):
        return 'ind'

    # Absoluto indexado X: $XXXX,X
    if re.match(r'^\$[0-9A-Fa-f]{4}\s*,\s*[Xx]$', operand):
        return 'abs,x'

    # Absoluto indexado Y: $XXXX,Y
    if re.match(r'^\$[0-9A-Fa-f]{4}\s*,\s*[Yy]$', operand):
        return 'abs,y'

    # Zero page indexado X: $XX,X
    if re.match(r'^\$[0-9A-Fa-f]{2}\s*,\s*[Xx]$', operand):
        return 'zp,x'

    # Zero page: $XX (exactamente 2 dígitos hex)
    if re.match(r'^\$[0-9A-Fa-f]{2}$', operand):
        return 'zp'

    # Absoluto: $XXXX (exactamente 4 dígitos hex)
    if re.match(r'^\$[0-9A-Fa-f]{4}$', operand):
        return 'abs'

    # Label o símbolo sin $ → tratar como absoluto
    return 'abs'


def parse_line(line: str):
    """
    Parsea una línea de ensamblador ca65.
    Retorna (mnemónico, operando) o None si la línea debe ignorarse.
    """
    # Eliminar comentario inline
    line = re.sub(r';.*$', '', line).strip()

    # Ignorar líneas vacías
    if not line:
        return None

    # Ignorar directivas ca65 (empiezan con .)
    if line.startswith('.'):
        return None

    # Ignorar labels puros (terminan en :), incluso con espacios antes
    # Un label puro es solo "nombre:" sin instrucción después
    label_only = re.match(r'^[@\w]+\s*:\s*$', line)
    if label_only:
        return None

    # Eliminar label al inicio si va seguido de instrucción: "loop: LDA $00"
    line = re.sub(r'^[@\w]+\s*:\s*', '', line).strip()

    if not line:
        return None

    # Extraer mnemónico e instrucción
    parts = line.split(None, 1)
    mnemonic = parts[0].upper()

    # Verificar que sea una instrucción 6502 conocida
    known_mnemonics = {key[0] for key in CYCLES}
    if mnemonic not in known_mnemonics:
        return None

    operand = parts[1].strip() if len(parts) > 1 else ''
    return mnemonic, operand


def analyze_file(filepath: str):
    """Lee y analiza el archivo ASM, imprime tabla de ciclos."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: No se encontro el archivo '{filepath}'")
        sys.exit(1)
    except IOError as e:
        print(f"Error al leer '{filepath}': {e}")
        sys.exit(1)

    results = []
    total_cycles = 0

    for lineno, raw_line in enumerate(lines, start=1):
        parsed = parse_line(raw_line)
        if parsed is None:
            continue

        mnemonic, operand = parsed
        mode = detect_mode(mnemonic, operand)
        cycles = CYCLES.get((mnemonic, mode))

        display_operand = operand if operand else ''
        instruction_str = f"{mnemonic} {display_operand}".strip()

        if cycles is not None:
            total_cycles += cycles
            results.append((lineno, instruction_str, mode, cycles))
        else:
            # Modo no encontrado en la tabla; reportar con '?'
            results.append((lineno, instruction_str, mode, None))

    # Imprimir tabla
    sep = '\u2500' * 57
    print(f"Archivo: {filepath}")
    print(sep)
    print(f"{'Linea':>6}  {'Instruccion':<22} {'Modo':<12} {'Ciclos':>6}")
    print(sep)

    for lineno, instr, mode, cycles in results:
        cycles_str = str(cycles) if cycles is not None else '?'
        print(f"{lineno:>6}   {instr:<22} {mode:<12} {cycles_str:>6}")

    print(sep)
    print(f"Total de ciclos estimados: {total_cycles}")

    if total_cycles > VBLANK_CYCLE_BUDGET:
        print(f"ADVERTENCIA: El NMI handler debe completarse en < {VBLANK_CYCLE_BUDGET} ciclos")
        print(f"  EXCESO: {total_cycles - VBLANK_CYCLE_BUDGET} ciclos sobre el presupuesto de VBlank ({VBLANK_CYCLE_BUDGET} ciclos)")
    else:
        print(f"OK: dentro del presupuesto de VBlank ({VBLANK_CYCLE_BUDGET} ciclos)")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 cycle_counter.py <archivo.asm>")
        print("Ejemplo: python3 cycle_counter.py src/capybara.asm")
        sys.exit(1)

    filepath = sys.argv[1]
    analyze_file(filepath)


if __name__ == '__main__':
    main()
