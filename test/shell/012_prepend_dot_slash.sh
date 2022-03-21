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
rm -rf .git

cfbs --non-interactive init
cfbs --non-interactive add ./test_policy.cf
cfbs --non-interactive remove ./test_policy.cf --non-interactive

rm cfbs.json
rm -rf .git
cfbs --non-interactive init
cfbs --non-interactive add test_policy.cf
cfbs --non-interactive remove test_policy.cf --non-interactive

rm cfbs.json
rm -rf .git
cfbs --non-interactive init
cfbs --non-interactive add ./test_policy.cf
cfbs --non-interactive remove test_policy.cf --non-interactive

rm cfbs.json
rm -rf .git
cfbs --non-interactive init
cfbs --non-interactive add test_policy.cf
cfbs --non-interactive remove ./test_policy.cf --non-interactive
