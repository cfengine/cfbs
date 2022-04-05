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
! grep '"name": "library-for-promise-types-in-python"' cfbs.json
! grep '"name": "promise-type-git"' cfbs.json

# Check that clean does nothing:
cat cfbs.json > before.json
cfbs --non-interactive clean
diff cfbs.json before.json
