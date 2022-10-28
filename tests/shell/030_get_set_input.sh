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

# Igor asks for input
cfbs get-input create-single-file - > actual.output
echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?"
  }
]' > expected.output
diff actual.output expected.output

# Igor adds response with some php magic
echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/test-1.txt"
  }
]' | cfbs set-input create-single-file -

# Igor asks for input again
cfbs get-input create-single-file - > actual.output
echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/test-1.txt"
  }
]' > expected.output
diff actual.output expected.output

# Igor changes the response to something else
echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/test-2.txt"
  }
]' | cfbs set-input create-single-file -

# Igor asks for input once again
cfbs get-input create-single-file actual.output
echo '[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/test-2.txt"
  }
]' > expected.output
diff actual.output expected.output

# Igor changes the wrong value
echo '[
  {
    "type": "string",
    "variable": "bogus",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/test-2.txt"
  }
]' > igors-input.json
! cfbs set-input create-single-file igors-input.json

# Now Igor instead changes a key
echo '[
  {
    "doofus": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/test-2.txt"
  }
]' > igors-input.json
! cfbs set-input create-single-file igors-input.json

# Igor changes the order but that's all right
echo '[
  {
    "variable": "filename",
    "type": "string",
    "label": "Filename",
    "response": "/tmp/test-3.txt",
    "question": "What file should this module create?"
  }
]' | cfbs set-input create-single-file -

# Igor asks for input and now the order is different
cfbs get-input create-single-file actual.output
echo '[
  {
    "variable": "filename",
    "type": "string",
    "label": "Filename",
    "response": "/tmp/test-3.txt",
    "question": "What file should this module create?"
  }
]' > expected.output
diff actual.output expected.output

echo "Igor is happy!"
