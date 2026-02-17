source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs --non-interactive add https://github.com/basvandervlies/cf_surfsara_lib@09e07dda690f5806d5f17be8e71d9fdcc51bbdf1

assert_file_contains cfbs.json https://github.com/basvandervlies/cf_surfsara_lib
assert_file_contains cfbs.json 09e07dda690f5806d5f17be8e71d9fdcc51bbdf1
assert_file_contains cfbs.json scl

cfbs build
assert_file_exists out/masterfiles/lib/scl/
assert_file_contains out/masterfiles/scl_example.json scl_dmidecode_example

# Build should be possible to do on another machine
# so let's test that it works after deleting the things which
# will not be on the next machine.
# Notably, cfbs add will download some things which can be reused in
# cfbs build (git clones / zip downloads in ~/.cfengine/cfbs)

rm -rf out/
rm -rf ~/.cfengine/cfbs

cfbs build
assert_file_exists out/masterfiles/lib/scl/
assert_file_contains out/masterfiles/scl_example.json scl_dmidecode_example

# Finally, let's also test that we can build it again (now with the cached
# files)

rm -rf out/

cfbs build
assert_file_exists out/masterfiles/lib/scl/
assert_file_contains out/masterfiles/scl_example.json scl_dmidecode_example

test_finish
