#!/bin/bash
# Copy the filled GDS (the submitted one) into release/ with checksums of both variants.
#   scripts/release.sh [name] [version]
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:-TEST3283}; VER=${2:-v.1.0.0}
REL=../../../release/$VER/gds
mkdir -p "$REL"
gzip -9 -n -c build/${NAME}.gds > "$REL/${NAME}.gds.gz"
( cd "$REL" && sha256sum ${NAME}.gds.gz > SHA256SUMS )
sha256sum build/${NAME}.gds build/${NAME}_nofill.gds
echo "release: $REL/${NAME}.gds.gz $(du -h "$REL/${NAME}.gds.gz" | cut -f1)"
