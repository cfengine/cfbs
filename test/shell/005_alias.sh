set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add mpf > output.log

grep "alias" output.log
grep "Added module" output.log
