set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -rf ./*

# A small index:

echo '{
  "name": "index",
  "description": "The official (default) index of modules for CFEngine Build",
  "type": "index",
  "index": {
    "autorun": {
      "description": "Enables autorun functionality.",
      "tags": ["supported", "management"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/olehermanse",
      "version": "1.0.1",
      "commit": "c3b7329b240cf7ad062a0a64ee8b607af2cb912a",
      "subdirectory": "management/autorun",
      "steps": ["json def.json def.json"]
    },
    "compliance-report-imports": {
      "name": "compliance-report-imports",
      "description": "Used by other modules to import compliance reports to Mission Portal.",
      "tags": ["experimental", "cfengine-enterprise"],
      "repo": "https://github.com/nickanderson/cfengine-security-hardening",
      "by": "https://github.com/nickanderson",
      "version": "0.0.8",
      "commit": "06f0894b662befbba4e775884f21cfe8573c32d6",
      "subdirectory": "./compliance-report-imports",
      "dependencies": ["autorun"],
      "steps": ["copy ./compliance-report-imports.cf services/autorun/"]
    },
    "compliance-report-lynis": {
      "description": "Compliance report with Lynis checks.",
      "tags": ["experimental", "security", "compliance"],
      "repo": "https://github.com/nickanderson/cfengine-lynis",
      "by": "https://github.com/nickanderson/",
      "version": "3.0.9",
      "commit": "9aaff7dd802cf879f40b992243e760f039e7636c",
      "subdirectory": "./compliance-reports",
      "dependencies": ["compliance-report-imports", "lynis"],
      "steps": [
        "copy ./generated-compliance-report.json .no-distrib/compliance-report-definitions/lynis-compliance-report.json"
      ]
    },
    "lynis": {
      "description": "Automates the installation, running, and reporting of CISOfys lynis system audits.",
      "tags": ["security", "compliance"],
      "repo": "https://github.com/nickanderson/cfengine-lynis",
      "by": "https://github.com/nickanderson",
      "version": "3.0.9",
      "commit": "9aaff7dd802cf879f40b992243e760f039e7636c",
      "steps": [
        "copy policy/main.cf services/lynis/main.cf",
        "json cfbs/def.json def.json"
      ]
    }
  }
}
' > cfbs.json

cfbs validate

# Missing dependency in index:

echo '{
  "name": "index",
  "description": "The official (default) index of modules for CFEngine Build",
  "type": "index",
  "index": {
    "compliance-report-imports": {
      "description": "Used by other modules to import compliance reports to Mission Portal.",
      "tags": ["experimental", "cfengine-enterprise"],
      "repo": "https://github.com/nickanderson/cfengine-security-hardening",
      "by": "https://github.com/nickanderson",
      "version": "0.0.8",
      "commit": "06f0894b662befbba4e775884f21cfe8573c32d6",
      "subdirectory": "./compliance-report-imports",
      "dependencies": ["autorun"],
      "steps": ["copy ./compliance-report-imports.cf services/autorun/"]
    }
  }
}
' > cfbs.json

!( cfbs validate )

# Same, but without listing a dependency

echo '{
  "name": "index",
  "description": "The official (default) index of modules for CFEngine Build",
  "type": "index",
  "index": {
    "compliance-report-imports": {
      "description": "Used by other modules to import compliance reports to Mission Portal.",
      "tags": ["experimental", "cfengine-enterprise"],
      "repo": "https://github.com/nickanderson/cfengine-security-hardening",
      "by": "https://github.com/nickanderson",
      "version": "0.0.8",
      "commit": "06f0894b662befbba4e775884f21cfe8573c32d6",
      "subdirectory": "./compliance-report-imports",
      "steps": ["copy ./compliance-report-imports.cf services/autorun/"]
    }
  }
}
' > cfbs.json

cfbs validate

# A typical policy set project with some local policy files

echo '{
  "name": "Example project",
  "description": "Example description",
  "type": "policy-set",
  "git": true,
  "build": [
    {
      "name": "masterfiles",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF).",
      "tags": ["supported", "base"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "version": "3.21.3",
      "commit": "ca637d4e6148432a90b7db598a4137956c0e0282",
      "added_by": "cfbs add",
      "steps": [
        "run EXPLICIT_VERSION=3.21.3 EXPLICIT_RELEASE=1 ./prepare.sh -y",
        "copy ./ ./"
      ]
    },
    {
      "name": "./policy.cf",
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "added_by": "cfbs add",
      "dependencies": ["masterfiles"],
      "steps": [
        "copy ./policy.cf services/cfbs/policy.cf",
        "policy_files services/cfbs/policy.cf",
        "bundles my_bundle"
      ]
    },
    {
      "name": "./more.cf",
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "added_by": "cfbs add",
      "dependencies": ["./policy.cf"],
      "steps": [
        "copy ./more.cf services/cfbs/more.cf",
        "policy_files services/cfbs/more.cf",
        "bundles more"
      ]
    }
  ]
}' > cfbs.json

cfbs validate

# Removing the second module we'll have a missing dependency:

echo '{
  "name": "Example project",
  "description": "Example description",
  "type": "policy-set",
  "git": true,
  "build": [
    {
      "name": "masterfiles",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF).",
      "tags": ["supported", "base"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "version": "3.21.3",
      "commit": "ca637d4e6148432a90b7db598a4137956c0e0282",
      "added_by": "cfbs add",
      "steps": [
        "run EXPLICIT_VERSION=3.21.3 EXPLICIT_RELEASE=1 ./prepare.sh -y",
        "copy ./ ./"
      ]
    },
    {
      "name": "./more.cf",
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "added_by": "cfbs add",
      "dependencies": ["./policy.cf"],
      "steps": [
        "copy ./more.cf services/cfbs/more.cf",
        "policy_files services/cfbs/more.cf",
        "bundles more"
      ]
    }
  ]
}' > cfbs.json

!( cfbs validate )

# Dependency exists in index, but not in build - should error:

echo '{
  "name": "Example project",
  "description": "Example description",
  "type": "policy-set",
  "git": true,
  "build": [
    {
      "name": "./more.cf",
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "added_by": "cfbs add",
      "dependencies": ["masterfiles"],
      "steps": [
        "copy ./more.cf services/cfbs/more.cf",
        "policy_files services/cfbs/more.cf",
        "bundles more"
      ]
    }
  ]
}' > cfbs.json

!( cfbs validate )

# NOTE: This shell test just covers some basic cases
#       See the unit tests for more thorough testing of validation
