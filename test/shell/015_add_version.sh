set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs --non-interactive add groups@0.1.2 --non-interactive
grep '"version": "0.1.2"' cfbs.json
grep '"commit": "087a2fd81e1bbaf241dfa7bf39013efd9d8d348f"' cfbs.json
cfbs --non-interactive remove promise-type-groups --non-interactive
