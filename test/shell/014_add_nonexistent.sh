set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
! ( cfbs add bollocks > output.log 2>&1 )
grep -F "Error: Module 'bollocks' does not exist" output.log
