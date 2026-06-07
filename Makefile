CC      ?= cc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11 -fopenmp
BZDIR    = third_party/bzip2
BZSRC    = $(BZDIR)/blocksort.c $(BZDIR)/huffman.c $(BZDIR)/crctable.c \
           $(BZDIR)/randtable.c $(BZDIR)/compress.c $(BZDIR)/decompress.c \
           $(BZDIR)/bzlib.c
BZOBJ    = $(BZSRC:.c=.o)
LIBBZ2   = libbz2.a

SRC      = src/args.c src/block_reader.c src/bz_block.c src/writer.c src/main.c
OBJ      = $(SRC:.c=.o)
BIN      = pbzx

# bzip2's own sources are old C; do not enable -Wextra/-Werror on them.
BZ_CFLAGS   = -O2 -D_FILE_OFFSET_BITS=64 -Wall
PBZX_CFLAGS = $(CFLAGS) -I$(BZDIR)

C_TESTS = tests/test_libbz2 tests/test_args tests/test_block_reader \
          tests/test_bz_block tests/test_writer

.PHONY: all clean test
all: $(BIN)

$(LIBBZ2): $(BZOBJ)
	ar rcs $@ $^

$(BZDIR)/%.o: $(BZDIR)/%.c
	$(CC) $(BZ_CFLAGS) -c $< -o $@

src/%.o: src/%.c
	$(CC) $(PBZX_CFLAGS) -c $< -o $@

$(BIN): $(OBJ) $(LIBBZ2)
	$(CC) $(PBZX_CFLAGS) $(OBJ) $(LIBBZ2) -o $@

tests/test_libbz2: tests/test_libbz2.c $(LIBBZ2)
	$(CC) $(PBZX_CFLAGS) $^ -o $@
tests/test_args: tests/test_args.c src/args.o
	$(CC) $(PBZX_CFLAGS) $^ -o $@
tests/test_block_reader: tests/test_block_reader.c src/block_reader.o
	$(CC) $(PBZX_CFLAGS) $^ -o $@
tests/test_bz_block: tests/test_bz_block.c src/bz_block.o $(LIBBZ2)
	$(CC) $(PBZX_CFLAGS) $^ -o $@
tests/test_writer: tests/test_writer.c src/writer.o
	$(CC) $(PBZX_CFLAGS) $^ -o $@

test: $(C_TESTS) $(BIN)
	@for t in $(C_TESTS); do echo "== $$t =="; ./$$t || exit 1; done
	@if command -v pytest >/dev/null 2>&1; then pytest -q; else echo "pytest not found, skipping python tests"; fi

clean:
	rm -f $(BZOBJ) $(OBJ) $(LIBBZ2) $(BIN) $(C_TESTS)
