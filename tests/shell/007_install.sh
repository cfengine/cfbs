source "$(dirname "$0")/common.sh"
skip-unless-unsafe

set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf ~/.cfagent/inputs/

cfbs --non-interactive init
cfbs --non-interactive add autorun
cfbs install

ls ~/.cfagent/inputs/def.json
rm -rf ~/.cfagent/inputs/
