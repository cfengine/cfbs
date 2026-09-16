set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf copy-a-file out

# A project pinned to a masterfiles version older than 3.29
# must warn that files may silently not get synced to clients.
cp ../shell/064_input_file_check_mpf/example-cfbs.json cfbs.json
echo "some content" > source.txt

mkdir -p copy-a-file
printf 'bundle agent copy_a_file {\n  reports:\n      "Copying $(cfbs.source)";\n}\n' > copy-a-file/copy_a_file.cf

echo '[{"type": "file", "variable": "source", "namespace": "cfbs", "bundle": "copy_a_file", "label": "Source file", "question": "Which file should be copied?", "filetype": [".txt", ".log"], "response": "./source.txt"}]' > copy-a-file/input.json

# Building against masterfiles 3.27.1 must warn that it predates 3.29.
cfbs build 2>&1 | grep -q "requires masterfiles 3.29 or later, but version is 3.27.1"

rm -rf copy-a-file out source.txt
