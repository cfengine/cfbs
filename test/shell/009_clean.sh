set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add promise-type-git
grep '"name": "library-for-promise-types-in-python"' cfbs.json
grep '"name": "promise-type-git"' cfbs.json
cfbs remove promise-type-git --non-interactive
cfbs clean
! grep '"name": "library-for-promise-types-in-python"' cfbs.json
! grep '"name": "promise-type-git"' cfbs.json
