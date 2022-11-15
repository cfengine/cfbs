set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf create-single-file

cfbs --non-interactive init
cfbs --non-interactive add delete-files@0.0.1
echo '[
  {
    "type": "list",
    "variable": "files",
    "namespace": "delete_files",
    "bundle": "delete_files",
    "label": "Files",
    "subtype": [
      {
        "key": "path",
        "type": "string",
        "label": "Path",
        "question": "Path to file"
      },
      {
        "key": "why",
        "type": "string",
        "label": "Why",
        "question": "Why should this file be deleted?",
        "default": "Unknown"
      }
    ],
    "while": "Specify another file you want deleted on your hosts?",
    "response": [
      { "path": "/tmp/test1", "why": "Test 1" },
      { "path": "/tmp/test2", "why": "Test 2" }
    ]
  }
]' | cfbs set-input delete-files -

cfbs get-input delete-files - | cfbs set-input delete-files -
