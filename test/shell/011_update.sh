set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs status
cfbs add mpf
cfbs add systemd
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
cfbs add ./test_policy.cf

cfbs update
# This test currently just checks that cfbs update runs succesfully,
# and doesn't break the cfbs.json project config file
# TODO: Expand this test once we can add a specific version, and
#       check that update actually changes something

cfbs status
cfbs build

grep '"name": "autorun"' cfbs.json
grep '"name": "./test_policy.cf"' cfbs.json
ls out/masterfiles/services/autorun/test_policy.cf
