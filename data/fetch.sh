#!/usr/bin/env bash
# Generate synthetic benchmark inputs (+ best-effort Silesia download) into data/.
# All outputs are gitignored.
set -euo pipefail
cd "$(dirname "$0")"

gen() { # name size_mb kind
  local name=$1 mb=$2 kind=$3 bytes
  bytes=$((mb * 1024 * 1024))
  case "$kind" in
    zeros)  head -c "$bytes" /dev/zero    > "$name" ;;
    random) head -c "$bytes" /dev/urandom > "$name" ;;
    text)   yes "the quick brown fox jumps over the lazy dog" \
              | head -c "$bytes" > "$name" ;;
  esac
  echo "generated $name ($mb MB, $kind)"
}

gen zeros_64.bin  64 zeros
gen random_64.bin 64 random
gen text_64.bin   64 text

if command -v curl >/dev/null 2>&1; then
  if curl -fL -o silesia.zip \
       http://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip 2>/dev/null; then
    command -v unzip >/dev/null 2>&1 && unzip -o silesia.zip -d silesia >/dev/null
    echo "fetched Silesia corpus"
  else
    echo "silesia download failed; continuing with synthetic data only"
  fi
fi
echo "done. inputs in $(pwd)"
