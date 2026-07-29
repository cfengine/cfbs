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

cat > expected.output <<'EOF'
{
  "variables": {
    "cfbs:create_single_file.filename": {
      "value": "/tmp/create-single-file.txt",
      "comment": "Added by 'cfbs input'"
    }
  }
}
EOF

echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/create-single-file.txt"
  }
]' > actual.input

# Render the augment, from stdin to stdout:
cfbs render-input create-single-file - - < actual.input > actual.output
diff actual.output expected.output

# The same, using files instead of stdin and stdout:
cfbs render-input create-single-file actual.input actual.output
diff actual.output expected.output

# Rendering the input doesn't store anything in the project:
test ! -e create-single-file/input.json
