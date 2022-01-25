set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/

echo '
bundle agent test_bundle
{
  meta:
    "tags" slist => { "autorun" };
  reports:
    "test";
}
' > test_policy.cf

touch cfbs.json && rm cfbs.json
cfbs init
cfbs add ./test_policy.cf
cfbs remove ./test_policy.cf --non-interactive

rm cfbs.json
cfbs init
cfbs add test_policy.cf
cfbs remove test_policy.cf --non-interactive

rm cfbs.json
cfbs init
cfbs add ./test_policy.cf
cfbs remove test_policy.cf --non-interactive

rm cfbs.json
cfbs init
cfbs add test_policy.cf
cfbs remove ./test_policy.cf --non-interactive
