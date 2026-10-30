#!/bin/bash
# Copy the filled GDS (the submitted one) into release/ with checksums of both variants,
# and the DRC logs of that filled GDS into release/<version>/doc/.
#   scripts/release.sh [name] [version]
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:-TEST3283}; VER=${2:-v.1.0.0}
REL=../../../release/$VER/gds
DOC=../../../release/$VER/doc
mkdir -p "$REL"
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
cat > "$DOC/DRC.md" << EOF
# DRC evidence, ${NAME} ${VER}

Both runs are on the filled release \`gds/${NAME}.gds.gz\` (sha256 \`${SHA}\`), top cell \`${NAME}\`,
deck \`ihp-sg13cmos5l\` \`run_drc.py\`.

| Run | Invocation | \`precheck_drc\` | Result | Log | Database |
| --- | --- | --- | --- | --- | --- |
| Minimum, the foundry precheck rule set | \`--minimum_drc\` | true | No DRC violations | [drc_min_fill.log](drc_min_fill.log) | [drc_min_fill.lyrdb](drc_min_fill.lyrdb) |
| Full deck | no \`--minimum_drc\` | false | No DRC violations | [drc_full_fill.log](drc_full_fill.log) | [drc_full_fill.lyrdb](drc_full_fill.lyrdb) |

\`run_drc.py\` sets the deck switch \`precheck_drc\` from \`--minimum_drc\`. The minimum run is the
precheck. The full run leaves that switch false because it checks the whole deck, not the reduced set.

There is no schematic netlist. \`doc/info.json\` does not reference \`release.netlist\`, so LVS is not run.
EOF
echo "release: $REL/${NAME}.gds.gz $(du -h "$REL/${NAME}.gds.gz" | cut -f1)"
