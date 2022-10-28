set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles=3.18.1-1
grep '"name": "masterfiles"' cfbs.json
grep '"version": "3.18.1-1"' cfbs.json
grep '"commit": "b6e9eacc65c797f4c2b4a59056293636c320d0c9"' cfbs.json
cfbs build
cfbs --non-interactive update
! grep '"version": "3.18.1-1"' cfbs.json
! grep '"commit": "b6e9eacc65c797f4c2b4a59056293636c320d0c9"' cfbs.json
