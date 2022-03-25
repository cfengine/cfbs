set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
! ( cfbs --non-interactive add bollocks > output.log 2>&1 )
grep -F "Error: Module 'bollocks' does not exist" output.log
