git-must-track () {
  # $1: Path / filename
  # Error if the file has never been added:
  git ls-files --error-unmatch $1
}

git-no-diffs () {
  # Error if there are staged changes (added, not yet commited):
  git diff --exit-code --staged
  
  # Error if there are uncommited changes (to tracked files):
  git diff --exit-code
}

skip-unless-unsafe() {
    if [ "${UNSAFE_TESTS:-}" != 1 ]; then
        local name
        name=$(_test_name_from_path "${BASH_SOURCE[1]:-$0}")
        echo "--- SKIP: $name (unsafe tests disabled) ---"
        exit 0
    fi
}
