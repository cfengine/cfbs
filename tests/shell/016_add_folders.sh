source "$(dirname "$0")/testlib.sh"
test_init

mkdir -p doofus
echo 'bundle agent doofus {
  reports:
      "This is $(this.promise_filename):$(this.bundle)!";
}
' > doofus/doofus.cf

mkdir -p doofus/foo
echo 'bundle agent foo {
  reports:
      "This is $(this.promise_filename):$(this.bundle)!";
}
' > doofus/foo/foo.cf

echo '{}
' > doofus/data.json

echo '{
  "vars": {
    "foo_thing": "awesome"
  }
}

' > doofus/foo/def.json

cfbs --non-interactive init
cfbs status

cfbs --non-interactive add ./doofus/
cfbs status

cfbs status | grep "./doofus/"
assert_file_contains cfbs.json '"name": "./doofus/"'
assert_file_contains cfbs.json '"directory ./ services/cfbs/doofus/"'
assert_file_contains cfbs.json '"policy_files services/cfbs/doofus/"'
assert_file_contains cfbs.json '"bundles doofus"'

cfbs build

assert_file_contains out/masterfiles/def.json '"inputs"'
assert_file_contains out/masterfiles/def.json '"services/cfbs/doofus/doofus.cf"'
assert_file_contains out/masterfiles/def.json '"services/cfbs/doofus/foo/foo.cf"'

assert_file_contains out/masterfiles/def.json '"control_common_bundlesequence_end"'
assert_file_contains out/masterfiles/def.json '"doofus"'

assert_file_contains out/masterfiles/def.json '"foo_thing": "awesome"'

assert_file_exists out/masterfiles/services/cfbs/doofus/doofus.cf
assert_file_exists out/masterfiles/services/cfbs/doofus/foo/foo.cf

test_finish
