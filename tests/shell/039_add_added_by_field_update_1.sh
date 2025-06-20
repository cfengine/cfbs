set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init

# Ensure adding a module during initialization is treated as adding manually
cat cfbs.json | grep -F "added_by" | grep -F "cfbs init"
# TODO: the case of custom non-masterfiles module(s) should also be tested

# Manually adding a module then manually adding its dependency should update the latter's `"added_by"` field in `cfbs.json`

cfbs --non-interactive add package-method-winget
cat cfbs.json | grep -F "added_by" | grep -F "package-method-winget"
[ "$(cat cfbs.json | grep -F "added_by" | grep -F "cfbs add" -c)" -eq 1 ]

cfbs --non-interactive add powershell-execution-policy
! ( cat cfbs.json | grep -F "added_by" | grep -F "package-method-winget" )
[ "$(cat cfbs.json | grep -F "added_by" | grep -F "cfbs add" -c)" -eq 2 ]
