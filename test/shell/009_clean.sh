set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs --non-interactive add promise-type-git
grep '"name": "library-for-promise-types-in-python"' cfbs.json
grep '"name": "promise-type-git"' cfbs.json
cfbs --non-interactive remove promise-type-git --non-interactive
cfbs --non-interactive clean || ret=$?
test $ret = "2"                 # there was nothing to clean
! grep '"name": "library-for-promise-types-in-python"' cfbs.json
! grep '"name": "promise-type-git"' cfbs.json
