set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs --non-interactive add https://github.com/basvandervlies/cf_surfsara_lib@09e07dda690f5806d5f17be8e71d9fdcc51bbdf1

grep https://github.com/basvandervlies/cf_surfsara_lib cfbs.json
grep 09e07dda690f5806d5f17be8e71d9fdcc51bbdf1 cfbs.json
grep scl cfbs.json

cfbs build
ls out/masterfiles/lib/scl/
grep scl_dmidecode_example out/masterfiles/scl_example.json

# Build should be possible to do on another machine
# so let's test that it works after deleting the things which
# will not be on the next machine.
# Notably, cfbs add will download some things which can be reused in
# cfbs build (git clones / zip downloads in ~/.cfengine/cfbs)

rm -rf out/
rm -rf ~/.cfengine/cfbs

cfbs build
ls out/masterfiles/lib/scl/
grep scl_dmidecode_example out/masterfiles/scl_example.json

# Finally, let's also test that we can build it again (now with the cached
# files)

rm -rf out/

cfbs build
ls out/masterfiles/lib/scl/
grep scl_dmidecode_example out/masterfiles/scl_example.json
