set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cp ../shell/049_remove_with_circular_dependencies/example-cfbs.json cfbs.json
cfbs validate

grep '"name": "example-module"' cfbs.json
grep '"name": "example-dependency"' cfbs.json

cfbs --non-interactive remove example-module --non-interactive
cfbs validate

! grep '"name": "example-module"' cfbs.json
! grep '"name": "example-dependency"' cfbs.json



cp ../shell/049_remove_with_circular_dependencies/example-cfbs.json cfbs.json
cfbs validate

grep '"name": "example-module"' cfbs.json
grep '"name": "example-dependency"' cfbs.json

cfbs --non-interactive remove example-dependency --non-interactive
cfbs validate

! grep '"name": "example-module"' cfbs.json
! grep '"name": "example-dependency"' cfbs.json
