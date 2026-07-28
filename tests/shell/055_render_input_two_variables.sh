set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf create-single-file-with-content

echo '{
  "build": [
    {
      "name": "create-single-file-with-content",
      "input": [
        {
          "type": "string",
          "variable": "filename",
          "label": "Filename",
          "question": "What file should this module create?"
        },
        {
          "type": "string",
          "variable": "content",
          "label": "Content",
          "question": "What content should this file have?"
        }
      ]
    }
  ]
}' > cfbs.json

echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/create-single-file.txt"
  },
  {
    "type": "string",
    "variable": "content",
    "label": "Content",
    "question": "What content should this file have?",
    "response": "Hello CFEngine!"
  }
]' | cfbs render-input create-single-file-with-content - - > actual.output

cat > expected.output <<'EOF'
{
  "variables": {
    "cfbs:create_single_file_with_content.filename": {
      "value": "/tmp/create-single-file.txt",
      "comment": "Added by 'cfbs input'"
    },
    "cfbs:create_single_file_with_content.content": {
      "value": "Hello CFEngine!",
      "comment": "Added by 'cfbs input'"
    }
  }
}
EOF
diff actual.output expected.output
