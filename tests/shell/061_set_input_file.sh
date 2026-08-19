set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf copy-a-file

echo '{
  "name": "Example",
  "type": "policy-set",
  "description": "Example description",
  "git": false,
  "build": [
    {
      "name": "copy-a-file",
      "description": "Copy a file.",
      "steps": ["input ./input.json def.json"],
      "input": [
        {
          "type": "file",
          "variable": "source",
          "namespace": "cfbs",
          "bundle": "copy_a_file",
          "label": "Source file",
          "question": "Which file should be copied?"
        }
      ]
    }
  ]
}' > cfbs.json

# A file from outside the project must be copied into the module's directory,
# with the response replaced by the path of that copy:
echo "some content" > /tmp/cfbs-notes.txt
echo '[{"type": "file", "variable": "source", "namespace": "cfbs", "bundle": "copy_a_file", "label": "Source file", "question": "Which file should be copied?", "response": "/tmp/cfbs-notes.txt"}]' | cfbs set-input copy-a-file -
grep '"response": "./copy-a-file/cfbs-notes.txt"' copy-a-file/input.json
test "$(cat copy-a-file/cfbs-notes.txt)" = "some content"
rm -f /tmp/cfbs-notes.txt

# A file already part of the project must be referred to as it is, without
# copying it into the module's directory:
echo "already here" > existing.txt
echo '[{"type": "file", "variable": "source", "namespace": "cfbs", "bundle": "copy_a_file", "label": "Source file", "question": "Which file should be copied?", "response": "./existing.txt"}]' | cfbs set-input copy-a-file -
grep '"response": "./existing.txt"' copy-a-file/input.json
test ! -f copy-a-file/existing.txt

rm -rf copy-a-file existing.txt
