set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs status
cfbs --non-interactive add mpf
cfbs status
echo '
bundle agent test_bundle
{
  meta:
    "tags" slist => { "autorun" };
  reports:
    "test";
}
' > test_policy.cf
cfbs --non-interactive add ./test_policy.cf
grep '"name": "autorun"' cfbs.json
grep '"name": "./test_policy.cf"' cfbs.json
cfbs status
cfbs build
ls out/masterfiles/services/autorun/test_policy.cf
