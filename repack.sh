#!/usr/bin/env bash
set -e -x

#
# Remove 'extra_requires' from the wheel
#
# The 'extras' are only useful with the full source distribution.
#

WORK="$(mktemp -d -t fm-twine-repack-XXXXXX)"
wheel unpack -d "$WORK" dist/*.whl
grep -Ev "^(Provides-Extra: .*|Requires-Dist: .*;.* extra == .*)$" "$WORK"/*/*.dist-info/METADATA > "$WORK"/METADATA.new
mv "$WORK"/METADATA.new "$WORK"/*/*.dist-info/METADATA
wheel pack -d dist "$WORK"/*
rm -rf "$WORK"

#
# Remove `@git+` requires from the source
#
# PyPI is now rejecting these.
#

WORK="$(mktemp -d -t fm-twine-repack-XXXXXX)"
TAR="$(ls dist/*.tar.*)"
tar -C "$WORK" -xvaf "$TAR"
sed -Ei 's/^(Requires-Dist:\s*[A-Za-z0-9][A-Za-z0-9._-]*)\s*@\s*([^ ]+)(.*)$/\1\3/' "$WORK"/*/PKG-INFO
FN="$(ls "$WORK")"
rm "$TAR"
tar -C "$WORK" -cvaf "$TAR" "$FN"
rm -rf "$WORK"
