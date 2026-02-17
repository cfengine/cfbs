source "$(dirname "$0")/testlib.sh"
test_init
rm -rf delete-files

cp ../shell/042_update_from_url/example-cfbs.json cfbs.json
cfbs validate

cp -r ../shell/042_update_from_url/delete-files .

cfbs --loglevel=debug --non-interactive update
assert_file_contains cfbs.json 'Specify another file you want deleted on your hosts?'
assert_file_contains cfbs.json 'Why should this file be deleted?'

test_finish
