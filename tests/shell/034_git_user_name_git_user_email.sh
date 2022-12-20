set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -rf cfbs.json .git 

# Check that the options '--git-user-name' and '--git-user-email' is not
# ignored by the 'set-input' command.

cfbs --non-interactive init
cfbs --non-interactive add delete-files@0.0.1

cat <<EOF | cfbs --git-user-name=foo --git-user-email=bar@baz set-input delete-files -
[
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
    "response": [{"path": "/tmp/bogus", "why": "Because I say so"}]
  }
]
EOF

git log -n1 | grep "Author: foo <bar@baz>"
