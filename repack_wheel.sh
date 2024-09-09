#!/usr/bin/env bash
set -e -x

#
# Remove 'extra_requires' from the wheel
#
# The 'extras' are only useful with the full source distribution.
#

WORK="$(mktemp -d -t wcm-twine-repack-XXXXXX)"
wheel unpack -d "$WORK" dist/WebCompatManager-*.whl
grep -Ev "^(Provides-Extra: .*|Requires-Dist: .* ; extra == '.*')$" "$WORK"/WebCompatManager-*/WebCompatManager-*.dist-info/METADATA > "$WORK"/METADATA.new
mv "$WORK"/METADATA.new "$WORK"/WebCompatManager-*/WebCompatManager-*.dist-info/METADATA
wheel pack -d dist "$WORK"/WebCompatManager-*
rm -rf "$WORK"
