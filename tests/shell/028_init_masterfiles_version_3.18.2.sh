set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles=3.18.2
grep '"name": "masterfiles"' cfbs.json
grep '"version": "3.18.2"' cfbs.json
grep '"commit": "a87b7fea6f7a88808b327730a4ba784a3dc664eb"' cfbs.json
cfbs build
