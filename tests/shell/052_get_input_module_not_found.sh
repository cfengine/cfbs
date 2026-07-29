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

# Asks for the input of a module which is neither in the project nor in the
# index. This used to crash with an uncaught KeyError from the index, instead of
# reporting that the module was not found:
! cfbs get-input no-such-module-anywhere - 2> actual.error
grep "Module 'no-such-module-anywhere' not found" actual.error
! grep "Traceback" actual.error

# Asks for the input of a module where version does not exist
! cfbs get-input delete-files@9.9.9 - 2> actual.error
grep "Module 'delete-files@9.9.9' not found" actual.error
! grep "Traceback" actual.error
