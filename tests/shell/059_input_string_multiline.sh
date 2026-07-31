set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf create-single-file-with-content
cp ../shell/059_input_string_multiline/example-cfbs.json cfbs.json

cfbs --non-interactive input create-single-file-with-content
grep '"type": "string-multiline"' create-single-file-with-content/input.json
grep '"default": "Hello CFEngine!\\nBye CFEngine!"' create-single-file-with-content/input.json
grep '"response": "Hello CFEngine!\\nBye CFEngine!"' create-single-file-with-content/input.json

cfbs render-input create-single-file-with-content create-single-file-with-content/input.json actual.output
diff actual.output ../shell/059_input_string_multiline/expected-augment.json
