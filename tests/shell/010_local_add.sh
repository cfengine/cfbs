set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs status

echo 'bundle agent bogus_bundle {
  reports:
      "This is $(this.promise_filename):$(this.bundle)!";
}
' > bogus_file.cf


cfbs --non-interactive add ./bogus_file.cf

grep '"name": "./bogus_file.cf"' cfbs.json
grep '"copy ./bogus_file.cf services/cfbs/bogus_file.cf"' cfbs.json
grep '"policy_files services/cfbs/bogus_file.cf"' cfbs.json
grep '"bundles bogus_bundle"' cfbs.json

cfbs status
cfbs build

grep '"inputs"' out/masterfiles/def.json
grep 'bogus_file.cf' out/masterfiles/def.json

grep '"control_common_bundlesequence_end"' out/masterfiles/def.json
grep '"bogus_bundle"' out/masterfiles/def.json

ls out/masterfiles/services/cfbs/bogus_file.cf
