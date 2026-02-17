source "$(dirname "$0")/testlib.sh"
test_init
rm -rf delete-files

cfbs --non-interactive init
cfbs --non-interactive add delete-files@0.0.1

commit_a=$(git rev-parse HEAD)

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

commit_b=$(git rev-parse HEAD)

assert_not_equal "$commit_a" "$commit_b"

cfbs get-input delete-files - | cfbs set-input delete-files -

commit_c=$(git rev-parse HEAD)

assert_equal "$commit_b" "$commit_c"

assert_git_tracks delete-files/input.json
assert_git_no_diffs

test_finish
