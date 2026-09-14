set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -f cfbs.json
rm -rf .git
rm -rf copy-files
cp ../shell/065_remove_input_w_files/example-cfbs.json cfbs.json

srcdir=$(mktemp -d)
cleanup() {
  rm -rf "$srcdir"
}
trap cleanup EXIT QUIT TERM

echo "one" > "$srcdir/one.txt"
echo "two" > "$srcdir/two.txt"

printf "$srcdir/one.txt\nyes\n$srcdir/two.txt\nno\n" | cfbs input copy-files

test -f copy-files/one.txt
test -f copy-files/two.txt
test -f copy-files/input.json

cfbs remove-input copy-files

if test -f copy-files/one.txt; then exit 1; fi
if test -f copy-files/two.txt; then exit 1; fi
if test -f copy-files/input.json; then exit 1; fi

rm -rf "$srcdir/one.txt" "$srcdir/two.txt" copy-files

