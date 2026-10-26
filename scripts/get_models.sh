#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# Fetches the offline speech and translation models for Übersetzen (German <-> French) into models/ (git-ignored).
# Speech: Vosk's small German and French models, checked against their sha256. Translation: Helsinki-NLP's Opus-MT
# de-fr and fr-de at a pinned revision, converted to CTranslate2 int8 in a throwaway container (about 1 GB of
# downloads the first time; the models end up at about 310 MB). Nothing here sends speech anywhere.
#
#   ./scripts/get_models.sh            fetch what is missing
#   ./scripts/get_models.sh --check    say what is there, fetch nothing
set -euo pipefail
cd "$(dirname "$0")/.."
DIR=models
VOSK=(
  "vosk-model-small-de-0.15 b7e53c90b1f0a38456f4cd62b366ecd58803cd97cd42b06438e2c131713d5e43"
  "vosk-model-small-fr-0.22 cabf6180e177eb9b3a9a9d43a437bd5e549f3a7d09525e5d69a3fed787be12ad"
)
OPUS=(
  "de-fr 2b4fe242d21e50e89d2917fa4d0b3616d157e339"
  "fr-de db80d261062d75a60e1d4897f13673313a33d50b"
)
# the converter's own packages, pinned (they only run in the throwaway container)
PIP="ctranslate2==4.8.4 transformers==5.20.2 sentencepiece==0.2.2 torch==2.14.1"

have() { [ -d "$DIR/$1" ] && [ -n "$(ls -A "$DIR/$1")" ]; }
if [ "${1:-}" = "--check" ]; then
  missing=0
  for v in "${VOSK[@]}"; do set -- $v; if have "$1"; then echo "ok       $1"; else echo "missing  $1"; missing=1; fi; done
  for o in "${OPUS[@]}"; do set -- $o; if have "opus-mt-$1-ct2"; then echo "ok       opus-mt-$1-ct2"; else echo "missing  opus-mt-$1-ct2"; missing=1; fi; done
  exit $missing
fi

mkdir -p "$DIR"
for v in "${VOSK[@]}"; do
  set -- $v
  have "$1" && { echo "have $1"; continue; }
  echo "fetching $1…"
  tmp=$(mktemp -d)
  curl -sSfL -o "$tmp/$1.zip" "https://alphacephei.com/vosk/models/$1.zip"
  echo "$2  $tmp/$1.zip" | sha256sum -c --quiet || { echo "$1: wrong checksum, not kept" >&2; rm -rf "$tmp"; exit 1; }
  unzip -q "$tmp/$1.zip" -d "$DIR"
  rm -rf "$tmp"
done

todo=()
for o in "${OPUS[@]}"; do set -- $o; have "opus-mt-$1-ct2" && echo "have opus-mt-$1-ct2" || todo+=("$o"); done
if [ ${#todo[@]} -gt 0 ]; then
  command -v docker >/dev/null || { echo "docker is needed to convert the translation models" >&2; exit 1; }
  free=$(df -Pk "$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo /)" | awk 'NR==2 {print int($4 / 1048576)}')
  [ "$free" -ge 4 ] || { echo "the conversion needs about 4 GB free for a while (there are ${free} GB)" >&2; exit 1; }
  script=""
  for o in "${todo[@]}"; do
    set -- $o
    script+="ct2-transformers-converter --model Helsinki-NLP/opus-mt-$1 --revision $2 --output_dir /out/opus-mt-$1-ct2"
    script+=" --quantization int8 --copy_files source.spm target.spm >/dev/null && echo converted opus-mt-$1-ct2; "
  done
  echo "converting ${#todo[@]} translation model(s) in a throwaway container…"
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$(pwd)/$DIR:/out" python:3.11-slim sh -c \
    "pip install -q --no-warn-script-location --extra-index-url https://download.pytorch.org/whl/cpu $PIP && export PATH=/tmp/.local/bin:\$PATH && $script"
fi

cat > "$DIR/README.md" <<EOF
# Models for Übersetzen (git-ignored)

Fetched by \`scripts/get_models.sh\`; \`start.sh\` mounts this folder read-only at /models.

| Folder | What | Licence | Source |
|---|---|---|---|
| vosk-model-small-de-0.15 | German speech to text (Vosk, small) | Apache-2.0 | https://alphacephei.com/vosk/models (sha256 ${VOSK[0]#* }) |
| vosk-model-small-fr-0.22 | French speech to text (Vosk, small) | Apache-2.0 | https://alphacephei.com/vosk/models (sha256 ${VOSK[1]#* }) |
| opus-mt-de-fr-ct2 | German to French (Opus-MT, CTranslate2 int8) | Apache-2.0 (as its model card says) | https://huggingface.co/Helsinki-NLP/opus-mt-de-fr at ${OPUS[0]#* } |
| opus-mt-fr-de-ct2 | French to German (Opus-MT, CTranslate2 int8) | Apache-2.0 (as its model card says) | https://huggingface.co/Helsinki-NLP/opus-mt-fr-de at ${OPUS[1]#* } |
EOF
echo "models ready in $DIR/"
