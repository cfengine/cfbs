set -e
set -x
cd tests/
source shell/testlib.sh
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

assert_git_tracks def.json
assert_git_tracks policy.cf
assert_git_tracks foo/bar.json
assert_git_tracks foo/baz.cf
assert_git_no_diffs
