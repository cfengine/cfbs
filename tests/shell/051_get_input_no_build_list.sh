set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf delete-files

# A cfbs.json for a module, that only uses "provides" (not "build"). Looking up
# a module used to crash with an uncaught KeyError on the missing "build" key:
echo '{
  "name": "example-module",
  "type": "module",
  "description": "Example module which provides one module",
  "provides": {
    "example": {
      "description": "Example",
      "tags": ["example"],
      "steps": ["copy example.cf services/autorun/example.cf"]
    }
  }
}' > cfbs.json

# Ask for the input of a module in the index, from a project without a
# "build" list:
cfbs get-input delete-files@0.0.1 actual.output
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
    "while": "Specify another file you want deleted on your hosts?"
  }
]' > expected.output
diff actual.output expected.output
