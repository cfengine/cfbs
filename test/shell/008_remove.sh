set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add masterfiles
grep '"name": "masterfiles"' cfbs.json
cfbs remove masterfiles --non-interactive
! grep '"name": "masterfiles"' cfbs.json
