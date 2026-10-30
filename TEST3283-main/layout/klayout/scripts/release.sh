#!/bin/bash
# Copy the filled GDS (the submitted one) into release/ with checksums of both variants, its LVS netlist
# into release/<version>/netlist/, and the DRC and LVS evidence of that GDS into release/<version>/doc/.
#   scripts/release.sh [name] [version]
# The evidence is checked before anything is written: the DRC logs (flow.sh drc_min_fill, drc_full_fill)
# and the LVS log (flow.sh lvs) must be newer than build/<name>.gds, name it as their design and pass; the
# DRC logs must show the expected minimum switch, the LVS log the netlist build/<name>.cdl.
# Signoff.md is written from those log lines, not from a template.
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
CDL=$(realpath build/${NAME}.cdl)
check_lvs() {
    local log=build/lvs.log
    [ -f "$log" ] && [ -f "$CDL" ] || die "lvs: log or netlist missing"
    [ "$log" -nt "$GDS" ] && [ "$log" -nt "$CDL" ] || die "lvs: older than build/${NAME}.gds or its netlist"
    grep -qF "LVS checks on design $GDS on cell ${NAME}" "$log" || die "lvs: not a run on build/${NAME}.gds"
    grep -qF "Netlist file: $CDL" "$log" || die "lvs: not a run against build/${NAME}.cdl"
    grep -q "Congratulations! Netlists match" "$log" && grep -qE "Status +\| PASS" "$log" || die "lvs: no match"
}
check_lvs
# a release is a submission: never overwrite one by accident (FORCE=1 to replace it on purpose)
if [ -e "$REL/${NAME}.gds.gz" ] && gzip -9 -n -c build/${NAME}.gds | cmp -s - "$REL/${NAME}.gds.gz"; then
    echo "release: $REL/${NAME}.gds.gz unchanged"
elif [ -e "$REL/${NAME}.gds.gz" ] && [ "${FORCE:-0}" != 1 ]; then
    echo "release: $REL/${NAME}.gds.gz exists and differs from build/${NAME}.gds; set FORCE=1 to replace it" >&2
    exit 1
else
    gzip -9 -n -c build/${NAME}.gds > "$REL/${NAME}.gds.gz"
    ( cd "$REL" && sha256sum ${NAME}.gds.gz > SHA256SUMS )
fi
sha256sum build/${NAME}.gds build/${NAME}_nofill.gds
NET=../../../release/$VER/netlist
mkdir -p "$DOC" "$NET"
cp build/${NAME}.cdl "$NET/${NAME}.cdl"
cp build/lvs.log "$DOC/lvs.log"
cp build/lvs/${NAME}_extracted.cir "$DOC/lvs_extracted.cir"
rm -f "$DOC/DRC.md"
cp build/drc_min_fill.log "$DOC/drc_min_fill.log"
cp build/drc_full_fill.log "$DOC/drc_full_fill.log"
cp "build/drc_min_fill/${NAME}_${NAME}_full.lyrdb" "$DOC/drc_min_fill.lyrdb"
cp "build/drc_full_fill/${NAME}_${NAME}_full.lyrdb" "$DOC/drc_full_fill.lyrdb"
SHA=$(awk '{print $1}' "$REL/SHA256SUMS")
logline() { grep -o "$2" "$DOC/$1" | sort -u; }
cat > "$DOC/Signoff.md" << EOF
# DRC and LVS evidence, ${NAME} ${VER}

## DRC

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

## LVS

Filled release GDS against [\`netlist/${NAME}.cdl\`](../netlist/${NAME}.cdl), deck \`ihp-sg13cmos5l\`
\`run_lvs.py\`, flat, \`--purge --purge_nets --ignore_top_ports_mismatch\`.
Result, from the log: $(logline lvs.log 'Netlists match') ($(logline lvs.log 'Status *| [A-Z]*' | tr -s ' ')).
Log: [lvs.log](lvs.log), extracted netlist: [lvs_extracted.cir](lvs_extracted.cir).

The netlist (\`scripts/lvs_netlist.py\`, from \`slots.csv\`) has one \`cap_cmomi\` per placed cell between
its tile's PLUS and MINUS pad nets: $(grep -c '^C' "$NET/${NAME}.cdl") instances in 44 tiles. OP, SHT, TH, LS, the
ground frame and the fill hold no device and are purged. What the comparison establishes, and what not:

- Checked: every tile has its capacitor (all copies of an array), between two nets of its own, with no net
  shared or shorted between tiles. Removing a tile's device or one copy of an array, adding a device, or
  moving a terminal to another tile's net fails (mutation runs of this netlist, 2026-10-30).
- Not checked, by the deck's design (\`lvs/testing/README.md\` of the PDK): \`w\`, \`l\`, \`mmin\`/\`mmax\`
  and \`feed\` (a device declared on the wrong metal band matches), and which pad is PLUS (the two terminals
  are equivalent). The build places the cells from \`slots.csv\`
  and \`check_conn.py\` checks PLUS on the left pad per tile.
- Port names are not compared: every tile labels its pads \`c1\`/\`c2\` (TEST9203 fixture), so the layout's
  top-level names repeat and cannot equal per-tile net names. Without the option the run reports only those
  88 name mismatches.
EOF
echo "release: $REL/${NAME}.gds.gz $(du -h "$REL/${NAME}.gds.gz" | cut -f1)"
