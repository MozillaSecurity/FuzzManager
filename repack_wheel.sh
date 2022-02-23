#!/usr/bin/env bash
set -e -x

#
# Remove 'extra_requires' from the wheel
#
# The 'extras' are only useful with the full source distribution.
#

WORK="$(mktemp -d -t fm-twine-repack-XXXXXX)"
wheel unpack -d "$WORK" dist/FuzzManager-*.whl
grep -Ev "^(Provides-Extra: .*|Requires-Dist: .* ; extra == '.*')$" "$WORK"/FuzzManager-*/FuzzManager-*.dist-info/METADATA > "$WORK"/METADATA.new
mv "$WORK"/METADATA.new "$WORK"/FuzzManager-*/FuzzManager-*.dist-info/METADATA
wheel pack -d dist "$WORK"/FuzzManager-*
rm -rf "$WORK"
