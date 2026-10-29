#!/bin/bash
# Build the nofill chip GDS. Usage: scripts/build.sh <ref TEST9203_nofill.gds> [top name]
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
REF=$1; NAME=${2:-TESTMOMI}
mkdir -p build
kl -zz -r scripts/klayout_run.py -rd script=scripts/build_chip.py -rd ref="$REF" -rd slots=slots.csv \
   -rd out=build/${NAME}_nofill.gds -rd name="$NAME" -rd pdk_rev="$(git -C "$PDK_TREE" rev-parse HEAD)"
