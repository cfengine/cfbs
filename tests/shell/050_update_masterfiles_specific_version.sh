#!/usr/bin/env bash
set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

# Inspect the masterfiles module specifically, rather than grepping the whole
# file (which could match a field belonging to a different module).
mf() { jq -r --arg k "$1" '.build[] | select(.name == "masterfiles") | .[$k]' cfbs.json; }
mf_has() { jq -r --arg k "$1" '.build[] | select(.name == "masterfiles") | has($k)' cfbs.json; }

# Start on an old version of masterfiles.
cfbs --non-interactive init --masterfiles=3.24.1
[ "$(mf version)" = "3.24.1" ]
[ "$(mf commit)" = "1171e2e50a229d78e2fdd4357a5d07ecc19bdbf4" ]

# Update to a specific intermediate version (not the latest). This must pin to
# exactly 3.24.4, not jump to the newest release in the index.
cfbs --non-interactive update masterfiles@3.24.4
[ "$(mf version)" = "3.24.4" ]
[ "$(mf commit)" = "ed4628805e352fd68d7d72664c859df5a4bb0715" ]
# Why we assert on "subdirectory" here: pinning an update to a version now routes
# through index.get_module_object() *with that version*, which reads the
# per-version index. That index stores an empty "subdirectory" ("") for modules
# that don't have one, and an empty subdirectory is invalid and breaks validation
# and build. So get_module_object() now has to drop it (matching how 'cfbs add'
# cleans the module up). This asserts it does not leak into cfbs.json, and the
# following 'cfbs validate' confirms the resulting module is actually valid.
[ "$(mf_has subdirectory)" = "false" ]
cfbs validate

# Asking again for the same version is a no-op.
cfbs --non-interactive update masterfiles@3.24.4
[ "$(mf version)" = "3.24.4" ]

# Asking for an older version than the current one must not downgrade.
cfbs --non-interactive update masterfiles@3.24.1
[ "$(mf version)" = "3.24.4" ]

# A plain update (no @version) still moves to a strictly newer version than the
# pin. Checking "!= 3.24.4" alone would also pass on a downgrade, so verify that
# 3.24.4 sorts before the new version (i.e. the new version is the greater one).
cfbs --non-interactive update masterfiles
new_ver="$(mf version)"
[ "$new_ver" != "3.24.4" ]
[ "$(printf '%s\n%s\n' "3.24.4" "$new_ver" | sort -V | tail -1)" = "$new_ver" ]

cfbs build
