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

# Input data straight from 'cfbs get-input', i.e. without any responses, renders
# an augment without any variables:
cfbs get-input create-single-file - | cfbs render-input create-single-file - - > actual.output
echo '{
  "variables": {}
}' > expected.output
diff actual.output expected.output
