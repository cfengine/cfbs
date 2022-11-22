set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf delete-files

cfbs --non-interactive init
cfbs --non-interactive add delete-files@0.0.1
echo '[
  {
    "bundle": "delete_files",
    "label": "Files",
    "namespace": "delete_files",
    "response": [
      {
        "path": "/tmp/test",
        "why": "no tests, please"
      }
    ],
    "subtype": [
      {
        "key": "path",
        "label": "Path",
        "question": "Path to file",
        "type": "string"
      },
      {
        "default": "Unknown",
        "key": "why",
        "label": "Why",
        "question": "Why should this file be deleted?",
        "type": "string"
      }
    ],
    "type": "list",
    "variable": "files",
    "while": "Specify another file you want deleted on your hosts?"
  }
]' | cfbs --log=debug set-input delete-files -

# Error if the file has never been added:
git ls-files --error-unmatch delete-files/input.json

# Error if there are staged (added, not yet commited)
git diff --exit-code --staged

# Error if there are uncommited changes (to tracked files):
git diff --exit-code
