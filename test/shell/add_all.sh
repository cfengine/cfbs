# This test is quite slow and makes many API requests,
# so not included in the normal sequence.
# We do something very similar in the index repo.

set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
cfbs --non-interactive add masterfiles
cfbs search | awk '{print $1}' | xargs -n1 cfbs --non-interactive add

cfbs build
