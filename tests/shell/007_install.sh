if [ x"$UNSAFE_TESTS" = x1 ]
then
    echo "Unsafe tests are enabled - running install test"
else
    echo "Warning: Unsafe tests are disabled - skipping install test"
    exit 0
fi

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
