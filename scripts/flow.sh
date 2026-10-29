#!/bin/bash
# Full serial flow: build -> connectivity -> fixture XOR -> fill -> min DRC (density) -> full DRC.
#   scripts/flow.sh <TEST9203_nofill.gds> [name]
set -e
cd "$(dirname "$0")/.."
REF=$1; NAME=${2:-TEST3283}
source scripts/env.sh
DECK=$PDK_TREE/ihp-sg13cmos5l/libs.tech/klayout/tech
drc() {  # drc <gds> <run_dir> [--min_drc]
    mkdir -p "$2"
    env -u KLAYOUT_PATH KLAYOUT_HOME="$KHOME" KLAYOUT_PATH="$PDK_TREE/ihp-sg13cmos5l/libs.tech/klayout" \
        PDK_ROOT="$PDK_TREE" PDK=ihp-sg13cmos5l python3 "$DECK/drc/run_drc.py" --path="$1" --topcell="$NAME" \
        --mp=1 --density_thr=8 --run_dir="$2" $3 > "$2.log" 2>&1 || true
    echo "$2: $(grep -E 'Violated rules|No DRC violations' "$2.log" | tail -1 | cut -d'|' -f3-)"
}
scripts/build.sh "$REF" "$NAME" > build/build.log 2>&1
echo "build: $(tail -1 build/build.log)"
kl -zz -r scripts/klayout_run.py -rd script=scripts/check_conn.py -rd gds=build/${NAME}_nofill.gds \
    -rd tiles=tiles.json -rd build=build/${NAME}_nofill_build.json -rd out=build/conn.json | tail -1
kl -zz -r scripts/klayout_run.py -rd script=scripts/check_fixture.py -rd a=build/${NAME}_nofill.gds \
    -rd b="$REF" -rd tiles=tiles.json | tail -2
kl -n sg13cmos5l -zz -r "$DECK/scripts/filler.py" -rd output_file=build/${NAME}.gds build/${NAME}_nofill.gds > build/fill.log 2>&1
echo "fill: $(tail -1 build/fill.log)"
drc build/${NAME}.gds build/drc_min_fill_${NAME} --min_drc
grep -E "(Metal[1-4]|TopMetal1|Activ|GatPoly) +Density %" build/drc_min_fill_${NAME}.log | sed 's/.*: //'
drc build/${NAME}.gds build/drc_full_fill_${NAME}
