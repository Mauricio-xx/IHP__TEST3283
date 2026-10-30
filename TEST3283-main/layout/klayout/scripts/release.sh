#!/bin/bash
# Copy the filled GDS (the submitted one) into release/ with checksums of both variants.
#   scripts/release.sh [name] [version]
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:-TEST3283}; VER=${2:-v.1.0.0}
REL=../../../release/$VER/gds
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
echo "release: $REL/${NAME}.gds.gz $(du -h "$REL/${NAME}.gds.gz" | cut -f1)"
