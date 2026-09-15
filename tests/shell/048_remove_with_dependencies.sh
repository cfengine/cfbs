set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cp ../shell/048_remove_with_dependencies/example-cfbs.json cfbs.json
cfbs validate

grep '"name": "example-module"' cfbs.json
grep '"name": "example-dependency"' cfbs.json

cfbs --non-interactive remove example-module --non-interactive
cfbs validate

if grep '"name": "example-module"' cfbs.json; then exit 1; fi
if grep '"name": "example-dependency"' cfbs.json; then exit 1; fi



cp ../shell/048_remove_with_dependencies/example-cfbs.json cfbs.json
cfbs validate

grep '"name": "example-module"' cfbs.json
grep '"name": "example-dependency"' cfbs.json

cfbs --non-interactive remove example-dependency --non-interactive
cfbs validate

grep '"name": "example-module"' cfbs.json
if grep '"name": "example-dependency"' cfbs.json; then exit 1; fi
