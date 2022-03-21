set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

echo '
{
  "name": "Example",
  "type": "policy-set",
  "description": "Example description",
  "build": [
    {
      "name": "promise-type-ansible",
      "version": "0.0.0",
      "commit": "invalid",
      "added_by": "cfbs add",
      "steps": []
    }
  ],
  "git": false
}
' > cfbs.json

cfbs --non-interactive update

# This is not perfect, it relies on the JSON formatting, and it doesn't check
# everything it could. Still, it tests a lot and was really easy to add.
# Also, it should not break on new commits(!)
# TODO: Use jq, a python script, cfbs validate or something similar

cat cfbs.json | grep -F "name" | grep -F "Example"
cat cfbs.json | grep -F "type" | grep -F "policy-set"
cat cfbs.json | grep -F "description" | grep -F "Example description"

cat cfbs.json | grep -F "name" | grep -F "promise-type-ansible"
cat cfbs.json | grep -F "version" | grep -F "."
cat cfbs.json | grep -F "commit"
cat cfbs.json | grep -F "added_by" | grep -F "cfbs add"
cat cfbs.json | grep -F "steps"
cat cfbs.json | grep -F "copy ansible_promise.py modules/promises/"
cat cfbs.json | grep -F "append enable.cf services/init.cf"
cat cfbs.json | grep -F "tags" | grep -F "supported" | grep -F "promise-type"
cat cfbs.json | grep -F "by" | grep -F "https://github.com/tranchitella"
cat cfbs.json | grep -F "repo" | grep -F "https://github.com/cfengine/modules"
cat cfbs.json | grep -F "subdirectory" | grep -F "promise-types/ansible/"
cat cfbs.json | grep -F "dependencies" | grep -F "library-for-promise-types-in-python"
cat cfbs.json | grep -F "description" | grep -F "Promise type to run ansible playbooks"

cat cfbs.json | grep -F "name" | grep -F "library-for-promise-types-in-python"
cat cfbs.json | grep -F "description" | grep -F "Library enabling promise types implemented in python"
cat cfbs.json | grep -F "tags" | grep -F "supported" | grep -F "library"
cat cfbs.json | grep -F "repo" | grep -F "https://github.com/cfengine/modules"
cat cfbs.json | grep -F "by" | grep -F "https://github.com/cfengine"
cat cfbs.json | grep -F "version" | grep -F "."
cat cfbs.json | grep -F "commit"
cat cfbs.json | grep -F "subdirectory" | grep -F "libraries/python/"
cat cfbs.json | grep -F "added_by" | grep -F "promise-type-ansible"
cat cfbs.json | grep -F "steps" | grep -F "copy cfengine.py modules/promises/"

cfbs --non-interactive add mpf
cfbs status
cfbs build

ls out/masterfiles/promises.cf
ls out/masterfiles/modules/promises/ansible_promise.py
