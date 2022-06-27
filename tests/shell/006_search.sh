set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs search > all.log
cfbs search mpf > mpf.log
cfbs search masterfiles > masterfiles.log

grep "python" all.log
! grep "python" mpf.log
grep "masterfiles" mpf.log
grep "masterfiles" masterfiles.log
