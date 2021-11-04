set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf ~/.cfagent/inputs/

cfbs init
cfbs add mpf
cfbs add autorun
cfbs install

ls ~/.cfagent/inputs/def.json
rm -rf ~/.cfagent/inputs/
