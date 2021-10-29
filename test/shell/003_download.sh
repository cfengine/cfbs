set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add masterfiles
cfbs download

ls ~/.cfengine/cfbs/downloads/*
