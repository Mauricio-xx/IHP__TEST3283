#!/bin/bash
# Full serial flow: build -> connectivity -> fixture XOR -> lead table -> fill -> fill clearance -> min DRC (density)
# -> full DRC -> release. Any failed check stops the flow before release; the release is only written when
# both DRC runs on the filled GDS are clean.
#   scripts/flow.sh [TEST9203_nofill.gds(.gz)] [name]
# The whole flow holds the shared lock so it never overlaps with the EM runs on this machine.
set -eo pipefail
cd "$(dirname "$0")/.."
REF=$(realpath "${1:-ref/TEST9203_nofill.gds.gz}"); NAME=${2:-TEST3283}
LOCK=${HEAVY_LOCK:-/home/montanares/git/momi_char_chip/.heavy.lock}
source scripts/env.sh
DECK=$PDK_TREE/ihp-sg13cmos5l/libs.tech/klayout/tech
exec 9>"$LOCK"; flock 9
drc() {  # drc <gds> <run_dir> [--min_drc]
    mkdir -p "$2"
    env -u KLAYOUT_PATH KLAYOUT_HOME="$KHOME" KLAYOUT_PATH="$PDK_TREE/ihp-sg13cmos5l/libs.tech/klayout" \
        PDK_ROOT="$PDK_TREE" PDK=ihp-sg13cmos5l python3 "$DECK/drc/run_drc.py" --path="$1" --topcell="$NAME" \
        --mp=1 --density_thr=8 --run_dir="$2" $3 > "$2.log" 2>&1 || true
    echo "$2: $(grep -E 'Violated rules|No DRC violations' "$2.log" | tail -1 | cut -d'|' -f3-)"
}
mkdir -p build
scripts/build.sh "$REF" "$NAME" > build/build.log 2>&1
echo "build: $(tail -1 build/build.log)"
kl -zz -r scripts/klayout_run.py -rd script=scripts/check_conn.py -rd gds=build/${NAME}_nofill.gds \
    -rd tiles=tiles.json -rd build=build/${NAME}_nofill_build.json -rd out=build/conn.json | tail -1
kl -zz -r scripts/klayout_run.py -rd script=scripts/check_fixture.py -rd a=build/${NAME}_nofill.gds \
    -rd b="$REF" -rd tiles=tiles.json | tail -2
kl -zz -r scripts/klayout_run.py -rd script=scripts/lead_table.py -rd gds=build/${NAME}_nofill.gds -rd slots=slots.csv \
    -rd build=build/${NAME}_nofill_build.json -rd out=leads.csv \
    -rd itf="$PDK_TREE/ihp-sg13cmos5l/libs.tech/parasitics/itf/sg13cmos5l_typ.itf" | tail -1
kl -n sg13cmos5l -zz -r "$DECK/scripts/filler.py" -rd output_file=build/${NAME}.gds build/${NAME}_nofill.gds > build/fill.log 2>&1
echo "fill: $(tail -1 build/fill.log)"
kl -zz -r scripts/klayout_run.py -rd script=scripts/check_fill.py -rd fill=build/${NAME}.gds \
    -rd nofill=build/${NAME}_nofill.gds -rd tiles=tiles.json -rd build=build/${NAME}_nofill_build.json \
    -rd out=build/fill_check.json | tail -1
drc build/${NAME}.gds build/drc_min_fill --min_drc
grep -E "(Metal[1-4]|TopMetal1|Activ|GatPoly) +Density %" build/drc_min_fill.log | sed 's/.*: //'
drc build/${NAME}.gds build/drc_full_fill
drc build/${NAME}_nofill.gds build/drc_full_nofill
for d in drc_min_fill drc_full_fill; do
    grep -q "No DRC violations" build/$d.log || { echo "$d not clean, no release"; exit 1; }
done
scripts/release.sh "$NAME"
