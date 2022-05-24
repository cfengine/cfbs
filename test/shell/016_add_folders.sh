set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf one
rm -rf two

mkdir one
echo '
bundle agent bundle_one
{
  meta:
    "tags" slist => { "autorun" };
  reports:
    "one";
}
' > one/policy.cf
echo '{}
' > one/data.json

mkdir two
mkdir two/three
echo '
bundle agent bundle_two
{
  meta:
    "tags" slist => { "autorun" };
  reports:
    "two";
}
' > two/three/policy.cf
echo '{
  "vars": {
    "foo_thing": "awesome"
  }
}

' > two/three/def.json
echo 'Hello
' > two/three/file.txt

cfbs --non-interactive init
cfbs status

cfbs --non-interactive add ./one
cfbs --non-interactive add ./two/
cfbs status

cfbs status | grep "./one/"
cfbs status | grep "./two/"
cat cfbs.json | grep "directory ./ services/cfbs/one/"
cat cfbs.json | grep "directory ./ services/cfbs/two/"

cfbs build

ls out/masterfiles/services/cfbs/one
grep "bundle_one" out/masterfiles/services/cfbs/one/policy.cf
ls out/masterfiles/services/cfbs/one/data.json

ls out/masterfiles/services/cfbs/two
grep "bundle_two" out/masterfiles/services/cfbs/two/policy.cf
grep "Hello" out/masterfiles/services/cfbs/two/file.txt

grep "awesome" out/masterfiles/def.json
