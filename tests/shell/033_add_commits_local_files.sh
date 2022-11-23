set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -rf cfbs.json .git def.json policy.cf foo

cfbs --non-interactive init

cat <<EOF > def.json
{
  "variables": {
    "foo:bar.baz": {
      "value": "foobar",
      "comment": "foobaz"
    }
  }
}
EOF

cat <<EOF > policy.cf
bundle agent foo
{
  reports:
      "Hello from $(this.bundle)";
}
EOF

mkdir foo
cat <<EOF > foo/bar.json
{
  "classes": {
    "services_autorun_bundles": ["any::"]
  }
}
EOF

cat <<EOF > foo/baz.cf
bundle agent baz
{
  reports:
      "Hello from $(this.bundle)";
}
EOF

cfbs --non-interactive add ./def.json ./policy.cf ./foo

# Error if the file has never been added:
git ls-files --error-unmatch def.json policy.cf foo/bar.json foo/baz.cf

# Error if there are staged (added, not yet commited)
git diff --exit-code --staged

# Error if there are uncommited changes (to tracked files):
git diff --exit-code
