#!/usr/bin/env bash
set -e

# Usage:
#   ./run_talkinggaussian.sh infer --wav /app/static/audios/input.wav --out /app/static/videos/out.mp4
# Optional:
#   --extractor deepspeech|hubert   (default deepspeech)
#   --dataset  data/May
#   --model    output/talking_May
#   --sh_degree 0|1|2|3            (default 2, rendering quality level)

MODE="$1"; shift || true

if [ "$MODE" != "infer" ]; then
  echo "Only infer is supported."
  exit 1
fi

WAV=""
OUT=""
EXTRACTOR="deepspeech"
DATASET="data/May"
MODEL="output/talking_May"
SH_DEGREE="2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wav) WAV="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --extractor) EXTRACTOR="$2"; shift 2;;
    --dataset) DATASET="$2"; shift 2;;
    --model) MODEL="$2"; shift 2;;
    --sh_degree) SH_DEGREE="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [ -z "$WAV" ] || [ -z "$OUT" ]; then
  echo "Missing --wav or --out"
  exit 1
fi

# We reuse your tested Python pipeline (feature -> synthesize -> trim -> mux)
# It creates final mp4 in test_result/<basename>_final.mp4
# Use conda run to switch to talking_gaussian environment
# Note: Need to change to TalkingGaussian directory before running Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Convert relative paths to absolute paths (relative to project root)
if [[ "$WAV" != /* ]]; then
  WAV="$PROJECT_ROOT/$WAV"
fi
if [[ "$OUT" != /* ]]; then
  OUT="$PROJECT_ROOT/$OUT"
fi

cd "$SCRIPT_DIR" || exit 1

# Convert paths to relative paths (relative to TalkingGaussian directory) or keep absolute
# Python script will handle path resolution automatically
WAV_REL=$(realpath --relative-to="$SCRIPT_DIR" "$WAV" 2>/dev/null || echo "$WAV")
OUT_REL=$(realpath --relative-to="$SCRIPT_DIR" "$OUT" 2>/dev/null || echo "$OUT")

# Convert audio file path: if it's relative to project root, convert to relative to TalkingGaussian
# Python script will handle both relative and absolute paths
AUDIO_ARG="$WAV"
if [[ "$AUDIO_ARG" != /* ]]; then
  # Relative path: try relative to TalkingGaussian first, then relative to project root
  if [[ "$AUDIO_ARG" == ../* ]] || [[ "$AUDIO_ARG" == static/* ]]; then
    # Path like "../static/audios/input.wav" or "static/audios/input.wav"
    # Keep as-is, Python script will resolve it
    AUDIO_ARG="$AUDIO_ARG"
  else
    # Try relative to TalkingGaussian directory
    AUDIO_ARG="$WAV_REL"
  fi
fi

conda run -n talking_gaussian --no-capture-output \
    python test_talkinggaussian.py \
    --audio_file "$AUDIO_ARG" \
    --audio_extractor "$EXTRACTOR" \
    --dataset_path "$DATASET" \
    --model_path "$MODEL" \
    --output_dir "test_result" \
    --sh_degree "$SH_DEGREE"

# Find final file and copy to OUT
BASENAME="$(basename "$WAV_REL")"
NAME="${BASENAME%.*}"
FINAL="test_result/${NAME}_final.mp4"

if [ ! -f "$FINAL" ]; then
  echo "Final mp4 not found: $FINAL"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"

# Also timestamp the intermediate artifacts if present.
for f in "test_result/${NAME}_talking_head.mp4" "test_result/${NAME}_trimmed.mp4"; do
  if [ -f "$f" ]; then
    mv -f "$f" "${f%.mp4}_${TS}.mp4"
  fi
done

# Timestamp the final artifact in test_result.
FINAL_TS="test_result/${NAME}_${TS}_final.mp4"
mv -f "$FINAL" "$FINAL_TS"

# Write to a timestamped OUT path (derived from --out).
OUT_DIR="$(dirname "$OUT")"
OUT_BASE="$(basename "$OUT")"
OUT_STEM="${OUT_BASE%.*}"
OUT_EXT="${OUT_BASE##*.}"
OUT_TS="$OUT_DIR/${OUT_STEM}_${TS}.${OUT_EXT}"

mkdir -p "$OUT_DIR"

# Convert FINAL_TS to absolute path for comparison
FINAL_ABS="$(readlink -f "$FINAL_TS" 2>/dev/null || echo "$SCRIPT_DIR/$FINAL_TS")"
OUT_ABS="$(readlink -f "$OUT_TS" 2>/dev/null || echo "$OUT_TS")"

if [ "$FINAL_ABS" = "$OUT_ABS" ]; then
  echo "OK: $OUT_TS (already at destination)"
  exit 0
fi

cp -f "$FINAL_TS" "$OUT_TS"
echo "OK: $OUT_TS"
