set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf delete-files

cp ../shell/039_update_from_url/example-cfbs.json cfbs.json
cp -r ../shell/039_update_from_url/delete-files .

cfbs --loglevel=debug --non-interactive update
grep 'Specify another file you want deleted on your hosts?' delete-files/input.json
