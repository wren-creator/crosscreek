#!/usr/bin/env bash
# Package the syllabus source tree into a valid .epub.
# mimetype must be the first entry and stored uncompressed.
set -euo pipefail
cd "$(dirname "$0")"

OUT="../Cross-Creek-101-Syllabus.epub"
rm -f "$OUT"

zip -X -0 "$OUT" mimetype >/dev/null
zip -X -9 -r "$OUT" META-INF OEBPS -x '.*' >/dev/null

echo "built $OUT"
unzip -l "$OUT"
