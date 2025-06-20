set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init

# Manually adding a dependency of a module then manually adding that module should not update the latter's `"added_by"` field in `cfbs.json`

cfbs --non-interactive add powershell-execution-policy
cat cfbs.json | grep -F "added_by" | grep -F "cfbs add"

cfbs --non-interactive add package-method-winget
! ( cat cfbs.json | grep -F "added_by" | grep -F "package-method-winget" )
