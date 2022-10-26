set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

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
grep '"name": "./doofus/"' cfbs.json
grep '"directory ./ services/cfbs/doofus/"' cfbs.json
grep '"policy_files services/cfbs/doofus/"' cfbs.json
grep '"bundles doofus"' cfbs.json

cfbs build

grep '"inputs"' out/masterfiles/def.json
grep '"services/cfbs/doofus/doofus.cf"' out/masterfiles/def.json
grep '"services/cfbs/doofus/foo/foo.cf"' out/masterfiles/def.json

grep '"control_common_bundlesequence_end"' out/masterfiles/def.json
grep '"doofus"' out/masterfiles/def.json

grep '"foo_thing": "awesome"' out/masterfiles/def.json

ls out/masterfiles/services/cfbs/doofus/doofus.cf
ls out/masterfiles/services/cfbs/doofus/foo/foo.cf
