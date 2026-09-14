set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -f cfbs.json
rm -rf .git
rm -rf write-notes
cp ../shell/063_input_string_multiline_in_list/example-cfbs.json cfbs.json

# A "string-multiline" must be an acceptable "subtype" of a "list" input:
cfbs validate

# Each note is read until a double newline, and the "while" prompt of the
# list then asks whether to write another:
cfbs input write-notes > actual.output <<EOF
Hello CFEngine!
Bye CFEngine!


yes
Just one line


no
EOF

cfbs render-input write-notes write-notes/input.json - > actual.augment
diff actual.augment ../shell/063_input_string_multiline_in_list/expected-augment.json

rm -rf write-notes actual.output actual.augment
