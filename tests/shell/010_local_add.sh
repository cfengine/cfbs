source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs status

echo 'bundle agent bogus_bundle {
  reports:
      "This is $(this.promise_filename):$(this.bundle)!";
}
' > bogus_file.cf


cfbs --non-interactive add ./bogus_file.cf

assert_file_contains cfbs.json '"name": "./bogus_file.cf"'
assert_file_contains cfbs.json '"copy ./bogus_file.cf services/cfbs/bogus_file.cf"'
assert_file_contains cfbs.json '"policy_files services/cfbs/bogus_file.cf"'
assert_file_contains cfbs.json '"bundles bogus_bundle"'

cfbs status
cfbs build

assert_file_contains out/masterfiles/def.json '"inputs"'
assert_file_contains out/masterfiles/def.json 'bogus_file.cf'

assert_file_contains out/masterfiles/def.json '"control_common_bundlesequence_end"'
assert_file_contains out/masterfiles/def.json '"bogus_bundle"'

assert_file_exists out/masterfiles/services/cfbs/bogus_file.cf

test_finish
