set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add masterfiles
cfbs --non-interactive add https://github.com/basvandervlies/cf_surfsara_lib@09e07dda690f5806d5f17be8e71d9fdcc51bbdf1

grep https://github.com/basvandervlies/cf_surfsara_lib cfbs.json
grep 09e07dda690f5806d5f17be8e71d9fdcc51bbdf1 cfbs.json
grep scl cfbs.json

cfbs build
ls out/masterfiles/lib/scl/
grep scl_dmidecode_example out/masterfiles/scl_example.json
