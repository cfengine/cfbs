set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles=no
!( grep '"name": "masterfiles"' cfbs.json )
cfbs status
!( cfbs build )
