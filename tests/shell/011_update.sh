source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs --non-interactive add promise-type-ansible@0.1.1
cfbs --non-interactive update promise-type-ansible@0.1.0
cfbs --non-interactive update

# This is not perfect, it relies on the JSON formatting, and it doesn't check
# everything it could. Still, it tests a lot and was really easy to add.
# Also, it should not break on new commits(!)
# TODO: Use jq, a python script, cfbs validate or something similar

assert_file_matches cfbs.json '"name".*"Example'
assert_file_matches cfbs.json '"type".*"policy-set"'
assert_file_matches cfbs.json '"description".*"Example description"'

assert_file_matches cfbs.json '"name".*"promise-type-ansible"'
assert_file_matches cfbs.json '"version":.*[0-9]+\.[0-9]+'
assert_file_contains cfbs.json '"commit"'
assert_file_matches cfbs.json '"added_by".*"cfbs add"'
assert_file_contains cfbs.json '"steps"'
assert_file_contains cfbs.json 'copy ansible_promise.py modules/promises/'
assert_file_contains cfbs.json 'append enable.cf services/init.cf'
assert_file_matches cfbs.json '"tags".*"supported"'
assert_file_matches cfbs.json '"by".*"https://github.com/tranchitella"'
assert_file_matches cfbs.json '"repo".*"https://github.com/cfengine/modules"'
assert_file_matches cfbs.json '"subdirectory".*"promise-types/ansible"'
assert_file_matches cfbs.json '"dependencies".*"library-for-promise-types-in-python"'
assert_file_matches cfbs.json '"description".*"Promise type to run ansible playbooks'

assert_file_matches cfbs.json '"name".*"library-for-promise-types-in-python"'
assert_file_matches cfbs.json '"description".*"Library enabling promise types implemented in python'
assert_file_matches cfbs.json '"tags".*"library"'
assert_file_matches cfbs.json '"repo".*"https://github.com/cfengine/modules"'
assert_file_matches cfbs.json '"by".*"https://github.com/cfengine"'
assert_file_matches cfbs.json '"subdirectory".*"libraries/python"'
assert_file_matches cfbs.json '"added_by".*"promise-type-ansible"'
assert_file_contains cfbs.json 'copy cfengine_module_library.py modules/promises/cfengine_module_library.py'

cfbs status
cfbs build

assert_file_exists out/masterfiles/promises.cf
assert_file_exists out/masterfiles/modules/promises/ansible_promise.py

test_finish
