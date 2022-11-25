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
