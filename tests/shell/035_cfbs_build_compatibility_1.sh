set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -rf ./*

# The purpose of this test is to ensure that older CFEngine Build projects
# still buid in newer versions of cfbs

# The below cfbs.json file was generated using cfbs 3.2.7
# which is the cfbs version shipped with CFEngine Enterprise 3.21.0

echo '{
  "name": "backwards-compatibility-test-1",
  "type": "policy-set",
  "description": "This project was set up to ensure projects created with CFEngine 3.21.0 / cfbs 3.2.7 still build as expected",
  "build": [
    {
      "name": "masterfiles",
      "version": "3.21.0",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF).",
      "tags": ["supported", "base"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "commit": "379c69aa71ab3069b2ef1c0cca526192fa77b864",
      "subdirectory": "",
      "added_by": "cfbs add",
      "steps": ["run ./prepare.sh -y", "copy ./ ./"]
    }
  ],
  "git": true
}
' > cfbs.json

# Most important, let's test that build works:
cfbs build

# Look for some proof that the build actually did something:
grep 'bundle common inventory' out/masterfiles/promises.cf

# These other commands should also work:
cfbs status

# NOTE: We expect cfbs build to work, but not cfbs validate since
#       this older module entry has an empty string for "subdirectory".
!( cfbs validate )

# Once more, but let's do download and build as separate steps:
rm -rf out/
rm -rf ~/.cfengine/cfbs

cfbs download

cfbs build

# Perform same checks again:
grep 'bundle common inventory' out/masterfiles/promises.cf

# Finally, let's see validation working if we fix the module:
rm -rf out/
rm -rf ~/.cfengine/cfbs

echo '{
  "name": "backwards-compatibility-test-1",
  "type": "policy-set",
  "description": "This project was set up to ensure projects created with CFEngine 3.21.0 / cfbs 3.2.7 still build as expected",
  "build": [
    {
      "name": "masterfiles",
      "version": "3.21.0",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF).",
      "tags": ["supported", "base"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "commit": "379c69aa71ab3069b2ef1c0cca526192fa77b864",
      "added_by": "cfbs add",
      "steps": ["run ./prepare.sh -y", "copy ./ ./"]
    }
  ],
  "git": true
}
' > cfbs.json

cfbs validate
