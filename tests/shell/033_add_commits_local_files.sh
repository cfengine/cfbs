set -e
set -x
cd tests/
source shell/common.sh
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

git-must-track def.json
git-must-track policy.cf
git-must-track foo/bar.json
git-must-track foo/baz.cf
git-no-diffs
