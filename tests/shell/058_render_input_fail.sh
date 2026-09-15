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
    },
    {
      "name": "autorun"
    }
  ]
}' > cfbs.json

# A changed value doesn't conform with the input definition:
echo '[
  {
    "type": "string",
    "variable": "bogus",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/create-single-file.txt"
  }
]' > actual.input
if cfbs render-input create-single-file actual.input -; then exit 1; fi

# Neither does a renamed key:
echo '[
  {
    "doofus": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/create-single-file.txt"
  }
]' > actual.input
if cfbs render-input create-single-file actual.input -; then exit 1; fi

# Input data which doesn't parse as json:
echo 'not json' > actual.input
if cfbs render-input create-single-file actual.input -; then exit 1; fi

# A module which doesn't accept any input:
echo '[]' > actual.input
if cfbs render-input autorun actual.input -; then exit 1; fi

# A module which doesn't exist:
if cfbs render-input no-such-module-anywhere actual.input -; then exit 1; fi

# A missing outfile, and one argument too many:
if cfbs render-input create-single-file actual.input; then exit 1; fi
if cfbs render-input create-single-file actual.input - -; then exit 1; fi
