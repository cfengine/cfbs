set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add mpf
cfbs add autorun
cfbs add systemd
cfbs add git
cfbs add ansible
cfbs build

ls out/
