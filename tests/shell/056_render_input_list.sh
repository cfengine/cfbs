set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf conditional-installer

# A module with an explicit namespace and bundle, and a list of responses:
echo '{
  "build": [
    {
      "name": "conditional-installer",
      "input": [
        {
          "type": "string",
          "variable": "packages_to_uninstall",
          "namespace": "conditional_installer",
          "bundle": "main",
          "label": "Uninstall",
          "question": "Which package(s) would you like to be uninstalled?"
        },
        {
          "type": "list",
          "variable": "packages_to_install",
          "namespace": "conditional_installer",
          "bundle": "main",
          "label": "Install",
          "subtype": [
            {
              "key": "packages",
              "type": "string",
              "label": "Package(s)",
              "question": "Package(s) to install"
            },
            {
              "key": "condition",
              "type": "string",
              "label": "Condition",
              "question": "Condition for where to install"
            }
          ],
          "while": "Do you want to specify more packages to be installed?"
        }
      ]
    }
  ]
}' > cfbs.json

echo '[
  {
    "type": "string",
    "variable": "packages_to_uninstall",
    "namespace": "conditional_installer",
    "bundle": "main",
    "label": "Uninstall",
    "question": "Which package(s) would you like to be uninstalled?",
    "response": "wget"
  },
  {
    "type": "list",
    "variable": "packages_to_install",
    "namespace": "conditional_installer",
    "bundle": "main",
    "label": "Install",
    "subtype": [
      {
        "key": "packages",
        "type": "string",
        "label": "Package(s)",
        "question": "Package(s) to install"
      },
      {
        "key": "condition",
        "type": "string",
        "label": "Condition",
        "question": "Condition for where to install"
      }
    ],
    "while": "Do you want to specify more packages to be installed?",
    "response": [
      { "packages": "curl", "condition": "linux" },
      { "packages": "vim", "condition": "any" }
    ]
  }
]' | cfbs render-input conditional-installer - - > actual.output

cat > expected.output <<'EOF'
{
  "variables": {
    "conditional_installer:main.packages_to_uninstall": {
      "value": "wget",
      "comment": "Added by 'cfbs input'"
    },
    "conditional_installer:main.packages_to_install": {
      "value": [
        { "packages": "curl", "condition": "linux" },
        { "packages": "vim", "condition": "any" }
      ],
      "comment": "Added by 'cfbs input'"
    }
  }
}
EOF
diff actual.output expected.output
