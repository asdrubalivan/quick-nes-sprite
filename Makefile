AS     = ca65
LD     = ld65
EMU    = fceux

BUILD  = build
SRC    = src
CHR    = chr

SOURCES = $(SRC)/main.asm
OBJ     = $(BUILD)/main.o
CONFIG  = game.cfg

.PHONY: all clean run

all: game.nes

game.nes: $(OBJ) $(CONFIG)
	@echo "Linkeando ROM..."
	$(LD) -C $(CONFIG) $(OBJ) -o $@ --mapfile $(BUILD)/game.map
	@echo "ROM generado: game.nes"

$(OBJ): $(SOURCES) | $(BUILD)
	@echo "Compilando $(SOURCES)..."
	$(AS) -t nes -I $(SRC) $(SOURCES) -o $@
	@echo "Compilado: $@"

$(BUILD):
	mkdir -p $(BUILD)

clean:
	@echo "Limpiando archivos generados..."
	rm -rf $(BUILD) game.nes
	@echo "Limpieza completa."

run: game.nes
	$(EMU) game.nes
