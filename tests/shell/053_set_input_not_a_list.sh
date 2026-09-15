set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf create-single-file

echo '{
  "build": [
    {
      "name": "create-single-file",
      "input": [
        {
          "type": "string",
          "variable": "filename",
          "label": "Filename",
          "question": "What file should this module create?"
        }
      ]
    }
  ]
}' > cfbs.json

# Input data which is not a list of input definitions used to crash with an
# uncaught TypeError, instead of reporting that it doesn't conform:
echo '0' > actual.input
if cfbs set-input create-single-file actual.input 2> actual.error; then exit 1; fi
grep "does not conform with input definition" actual.error
if grep "Traceback" actual.error; then exit 1; fi

# An empty object was silently accepted, since there was nothing to compare:
echo '{}' > actual.input
if cfbs set-input create-single-file actual.input 2> actual.error; then exit 1; fi
grep "does not conform with input definition" actual.error
if grep "Traceback" actual.error; then exit 1; fi

# None of it was stored in the project:
test ! -e create-single-file/input.json
