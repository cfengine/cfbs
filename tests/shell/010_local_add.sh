set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs status

echo 'bundle agent bogus {
  reports:
      "This is $(this.promise_filename):$(this.bundle)!";
}
' > bogus.cf


cfbs --non-interactive add ./bogus.cf

grep '"name": "./bogus.cf"' cfbs.json
grep '"policy_files ./bogus.cf"' cfbs.json
grep '"bundles bogus"' cfbs.json

cfbs status
cfbs build

grep '"inputs"' out/masterfiles/def.json
grep '"services/cfbs/bogus.cf"' out/masterfiles/def.json

grep '"control_common_bundlesequence_end"' out/masterfiles/def.json
grep '"bogus"' out/masterfiles/def.json

ls out/masterfiles/services/cfbs/bogus.cf
