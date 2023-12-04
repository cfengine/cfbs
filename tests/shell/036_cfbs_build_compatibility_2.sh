set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -rf ./*

# This test is identical to the previous test, except it has more modules.

echo '{
  "name": "backwards-compatibility-test-2",
  "type": "policy-set",
  "description": "This project was set up to ensure projects created with CFEngine 3.21.0 / cfbs 3.2.7 still build as expected",
  "build": [
    {
      "name": "masterfiles",
      "version": "3.21.0",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF).",
      "tags": ["supported", "base"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "commit": "379c69aa71ab3069b2ef1c0cca526192fa77b864",
      "subdirectory": "",
      "added_by": "cfbs add",
      "steps": ["run ./prepare.sh -y", "copy ./ ./"]
    },
    {
      "name": "autorun",
      "version": "1.0.0",
      "description": "Enables autorun functionality.",
      "tags": ["supported", "management"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/olehermanse",
      "commit": "be3bc015f6a19e945bb7a9fa0ed78c97e2cecf61",
      "subdirectory": "management/autorun",
      "added_by": "cfbs add",
      "steps": ["json def.json def.json"]
    },
    {
      "name": "inventory-systemd",
      "description": "Adds reporting data (inventory) for interesting things from systemd.",
      "tags": ["supported", "inventory", "systemd"],
      "repo": "https://github.com/nickanderson/cfengine-inventory-systemd",
      "by": "https://github.com/nickanderson",
      "version": "0.1.0",
      "commit": "4b9c0708173d3b5f0855a76063781e2258465788",
      "added_by": "cfbs add",
      "steps": [
        "copy ./policy/main.cf services/inventory-systemd/main.cf",
        "json cfbs/def.json def.json"
      ]
    },
    {
      "name": "every-minute",
      "description": "Makes policy fetching, evaluation, and reporting happen every minute.",
      "tags": ["management", "experimental"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/olehermanse",
      "version": "1.0.0-1",
      "commit": "74b6776ca4e120285f9c44e68ccf79eef84accfd",
      "subdirectory": "management/every-minute",
      "added_by": "demo",
      "steps": ["json def.json def.json"]
    },
    {
      "name": "demo",
      "description": "Enables convenient and insecure settings for demoing CFEngine.",
      "tags": ["management", "experimental"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/olehermanse",
      "version": "1.0.0",
      "commit": "05bf5e5b1c014018a7b93a524e035c1a21bcffa4",
      "subdirectory": "management/demo",
      "dependencies": ["autorun", "every-minute"],
      "added_by": "cfbs add",
      "steps": ["json def.json def.json"]
    }
  ],
  "git": true
}
' > cfbs.json

# Most important, let's test that build works:
cfbs build

# Look for some proof that these modules are actually being built into the policy set:
grep 'services_autorun' out/masterfiles/def.json
grep '"control_executor_splaytime": "1",' out/masterfiles/def.json
grep 'inventory_systemd_service_units_running' out/masterfiles/def.json
grep 'bundle common inventory' out/masterfiles/promises.cf
grep '$(paths.systemctl) list-units --type=service --state=running' out/masterfiles/services/inventory-systemd/main.cf

# These other commands should also work:
cfbs status

cfbs validate

# Once more, but let's do download and build as separate steps:
rm -rf out/
rm -rf ~/.cfengine/cfbs

cfbs download

cfbs build

# Perform same checks again:
grep 'services_autorun' out/masterfiles/def.json
grep '"control_executor_splaytime": "1",' out/masterfiles/def.json
grep 'inventory_systemd_service_units_running' out/masterfiles/def.json
grep 'bundle common inventory' out/masterfiles/promises.cf
grep '$(paths.systemctl) list-units --type=service --state=running' out/masterfiles/services/inventory-systemd/main.cf
