set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf copy-a-file
rm -rf run-scripts
cp ../shell/060_input_file/example-cfbs.json cfbs.json
echo "some content" > source.txt
echo "some content" > source.sh

# Interactively, a "file" input must reject a path that doesn't exist and
# prompt again, then accept a path that does exist:
printf '/does/not/exist.txt\n./source.txt\n' | cfbs input copy-a-file | grep "not found, please try again"
grep '"response": "./source.txt"' copy-a-file/input.json
rm -rf copy-a-file

# Interactively, a "file" input must reject a path whose extension doesn't
# match one of the module-specified "filetype" extensions, then accept one
# that does:
printf './source.sh\n./source.txt\n' | cfbs input copy-a-file | grep "does not have one of the accepted file extensions (.txt, .log), please try again"
grep '"response": "./source.txt"' copy-a-file/input.json
rm -rf copy-a-file

# In non-interactive mode, a "file" input must fall back to the "default"
# given in the input definition, without prompting or checking existence:
cfbs --non-interactive input copy-a-file
grep '"type": "file"' copy-a-file/input.json
grep '"response": "./source.txt"' copy-a-file/input.json

cfbs render-input copy-a-file copy-a-file/input.json actual.output
diff actual.output ../shell/060_input_file/expected-augment.json

# A "file" input with a "while" prompt must let the user supply multiple
# files. Files from outside the project must be copied into the module's
# directory, next to input.json, and "response" updated to a list of the
# (possibly localized) paths:
echo "echo one" > /tmp/one.sh
echo "echo two" > /tmp/two.sh
printf '/tmp/one.sh\nyes\n/tmp/two.sh\nno\n' | cfbs input run-scripts
grep '"response": \[' run-scripts/input.json
grep '"./run-scripts/one.sh"' run-scripts/input.json
grep '"./run-scripts/two.sh"' run-scripts/input.json
test -f run-scripts/one.sh
test -f run-scripts/two.sh
rm -rf run-scripts /tmp/one.sh /tmp/two.sh

# A "file" input with no "filetype" restriction must accept a file with no
# extension at all, without prompting for retry:
echo "some content" > source
printf './source\n' | cfbs input copy-any-file
grep '"response": "./source"' copy-any-file/input.json
rm -rf copy-any-file source
