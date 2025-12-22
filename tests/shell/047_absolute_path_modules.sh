set -e
set -x
cd tests/
mkdir -p ./tmp
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cleanup() {
   rm -rf /tmp/foo
}
trap cleanup EXIT QUIT TERM
mkdir -p /tmp/foo

export GIT_AUTHOR_NAME="github_actions"
export GIT_AUTHOR_EMAIL="github_actions@example.com"

# Add first commit
cp -r ../sample/foo/main.cf /tmp/foo/foo.cf
git init /tmp/foo
cd /tmp/foo
git add /tmp/foo/foo.cf
git -c user.name="$GIT_AUTHOR_NAME" -c user.email="$GIT_AUTHOR_EMAIL" commit -m "initial commit"
head_commit=$(git rev-parse HEAD)
cd -

# run cfbs
cfbs --non-interactive init --masterfiles no
cfbs --non-interactive add /tmp/foo 
cfbs build

grep "$head_commit" cfbs.json

# Add second commit
cp ../sample/bar/baz/main.cf /tmp/foo/baz.cf
cd /tmp/foo
git add /tmp/foo/baz.cf
git -c user.name="$GIT_AUTHOR_NAME" -c user.email="$GIT_AUTHOR_EMAIL" commit -m "second commit"
head_commit=$(git rev-parse HEAD)
cd -

# run cfbs
cfbs --non-interactive update
cfbs build

grep "$head_commit" cfbs.json
