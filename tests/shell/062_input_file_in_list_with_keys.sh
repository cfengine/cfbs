set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -f cfbs.json
rm -rf .git
rm -rf copy-files
cp ../shell/062_input_file_in_list_with_keys/example-cfbs.json cfbs.json

# Keep the files outside the project, so that they get copied into it:
srcdir=$(mktemp -d)
cleanup() {
  rm -rf "$srcdir"
}
trap cleanup EXIT QUIT TERM

echo "one" > "$srcdir/one.txt"
echo "two" > "$srcdir/two.txt"
echo "notes" > "$srcdir/notes.md"

# A "file" among the keys of a list "subtype" must be an acceptable
# input definition:
cfbs validate

# The "file" key must apply the same checks as a top level "file" input,
# rejecting a path whose extension isn't accepted and a path that doesn't
# exist, while the "string" keys beside it accept whatever is typed. The
# answers below are path, owner and mode for each file, then whether to add
# another - the empty answers accept the defaults from the definition:
cfbs input copy-files > actual.output <<EOF
$srcdir/notes.md
/does/not/exist.txt
$srcdir/one.txt
alice
0600
yes
$srcdir/two.txt


no
EOF
grep "does not have one of the accepted file extensions (.txt, .log), please try again" actual.output
grep "File '/does/not/exist.txt' not found, please try again" actual.output

# Only the file is copied into the module's directory, next to input.json:
test -f copy-files/one.txt
test -f copy-files/two.txt

# Each response is an object where the file has been replaced by the path of
# that copy, and the strings are as typed - or the definition's defaults,
# where the user just hit enter:
cfbs render-input copy-files copy-files/input.json - > actual.augment
diff actual.augment ../shell/062_input_file_in_list_with_keys/expected-augment.json

rm -rf copy-files actual.output actual.augment
