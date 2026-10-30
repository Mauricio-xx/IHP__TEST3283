#!/bin/bash
# Copy the filled GDS (the submitted one) into release/ with checksums of both variants,
# and the DRC logs of that filled GDS into release/<version>/doc/.
#   scripts/release.sh [name] [version]
# The DRC evidence is checked before anything is written: both logs (flow.sh drc_min_fill, drc_full_fill)
# must be newer than build/<name>.gds, name it as their design, pass, and show the expected minimum switch.
# DRC.md is written from those log lines, not from a template.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:-TEST3283}; VER=${2:-v.1.0.0}
REL=../../../release/$VER/gds
DOC=../../../release/$VER/doc
mkdir -p "$REL"
GDS=$(realpath build/${NAME}.gds)
die() { echo "release: $*, no release" >&2; exit 1; }
check_drc() {  # check_drc <run> <expected "Minimum DRC enabled" value>
    local log=build/$1.log db=build/$1/${NAME}_${NAME}_full.lyrdb
    [ -f "$log" ] && [ -f "$db" ] || die "$1: log or database missing"
    [ "$log" -nt "$GDS" ] && [ "$db" -nt "$GDS" ] || die "$1: older than build/${NAME}.gds"
    grep -qF "main checks on design $GDS, topcell: ${NAME}" "$log" || die "$1: not a run on build/${NAME}.gds"
    grep -q "No DRC violations" "$log" && ! grep -q "Violated rules" "$log" || die "$1: not clean"
    ! grep -q "<item>" "$db" || die "$1: database has violations"
    [ "$(grep -o 'Minimum DRC enabled: [a-z]*' "$log" | sort -u)" = "Minimum DRC enabled: $2" ] \
        || die "$1: expected 'Minimum DRC enabled: $2' in every deck"
}
check_drc drc_min_fill true
check_drc drc_full_fill false
# a release is a submission: never overwrite one by accident (FORCE=1 to replace it on purpose)
if [ -e "$REL/${NAME}.gds.gz" ] && [ "${FORCE:-0}" != 1 ]; then
    if gzip -9 -n -c build/${NAME}.gds | cmp -s - "$REL/${NAME}.gds.gz"; then
        echo "release: $REL/${NAME}.gds.gz unchanged"; exit 0
    fi
    echo "release: $REL/${NAME}.gds.gz exists and differs from build/${NAME}.gds; set FORCE=1 to replace it" >&2
    exit 1
fi
gzip -9 -n -c build/${NAME}.gds > "$REL/${NAME}.gds.gz"
( cd "$REL" && sha256sum ${NAME}.gds.gz > SHA256SUMS )
sha256sum build/${NAME}.gds build/${NAME}_nofill.gds
mkdir -p "$DOC"
cp build/drc_min_fill.log "$DOC/drc_min_fill.log"
cp build/drc_full_fill.log "$DOC/drc_full_fill.log"
cp "build/drc_min_fill/${NAME}_${NAME}_full.lyrdb" "$DOC/drc_min_fill.lyrdb"
cp "build/drc_full_fill/${NAME}_${NAME}_full.lyrdb" "$DOC/drc_full_fill.lyrdb"
SHA=$(awk '{print $1}' "$REL/SHA256SUMS")
logline() { grep -o "$2" "$DOC/$1" | sort -u; }
cat > "$DOC/DRC.md" << EOF
# DRC evidence, ${NAME} ${VER}

Both runs are on the filled release \`gds/${NAME}.gds.gz\` (sha256 \`${SHA}\`), top cell \`${NAME}\`,
deck \`ihp-sg13cmos5l\` \`run_drc.py\`.

| Run | Invocation (\`flow.sh\`) | Switch, from the log | Result, from the log | Log | Database |
| --- | --- | --- | --- | --- | --- |
| Minimum, the foundry precheck rule set | \`--min_drc\` | $(logline drc_min_fill.log 'Minimum DRC enabled: [a-z]*') | $(logline drc_min_fill.log 'No DRC violations') | [drc_min_fill.log](drc_min_fill.log) | [drc_min_fill.lyrdb](drc_min_fill.lyrdb) |
| Full deck | no \`--min_drc\` | $(logline drc_full_fill.log 'Minimum DRC enabled: [a-z]*') | $(logline drc_full_fill.log 'No DRC violations') | [drc_full_fill.log](drc_full_fill.log) | [drc_full_fill.lyrdb](drc_full_fill.lyrdb) |

\`--min_drc\` is an alias of \`run_drc.py --minimum_drc\`, which sets the deck switch \`precheck_drc\`. The
logs do not print the invocation; the deck prints that switch as \`Minimum DRC enabled\` (main and density
decks). The minimum run is the precheck. The full run leaves the switch false because it checks the whole
deck, not the reduced set. Neither database has a violation item.

There is no schematic netlist. \`doc/info.json\` does not reference \`release.netlist\`, so LVS is not run.
EOF
echo "release: $REL/${NAME}.gds.gz $(du -h "$REL/${NAME}.gds.gz" | cut -f1)"
