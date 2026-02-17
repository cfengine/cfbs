#!/usr/bin/env bash
# testlib.sh - Minimal test framework for cfbs shell tests
#
# Usage in test files:
#   source "$(dirname "$0")/testlib.sh"
#   test_init
#   ... test body ...
#   test_finish

# --- Internal state ---
_TEST_NAME=""
_TEST_START_TIME=""
_LAST_OUTPUT=""
_LAST_EXIT_CODE=0
_TESTLIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Internal helpers ---

_test_name_from_path() {
    basename "$1" .sh
}

_test_fail() {
    set +x
    echo "FAIL: $*" >&2
    return 1
}

# --- Lifecycle ---

skip_unless_unsafe() {
    if [ "x${UNSAFE_TESTS:-}" != x1 ]; then
        local name
        name=$(_test_name_from_path "${BASH_SOURCE[1]:-$0}")
        echo "--- SKIP: $name (unsafe tests disabled) ---"
        exit 0
    fi
}

test_init() {
    set -e
    set -x

    _TEST_NAME=$(_test_name_from_path "${BASH_SOURCE[1]:-$0}")

    rm -rf ./tests/tmp/
    mkdir -p ./tests/tmp/
    cd ./tests/tmp/

    _TEST_START_TIME=$(date +%s)
    echo "--- START: $_TEST_NAME ---" >&2
}

test_finish() {
    local end elapsed
    end=$(date +%s)
    elapsed=$(( end - _TEST_START_TIME ))
    set +x
    echo "--- PASS: $_TEST_NAME (${elapsed}s) ---" >&2
}

# --- Git assertions ---

assert_git_tracks() {
    # $1: Path / filename
    # Error if the file has never been added:
    git ls-files --error-unmatch "$1" || _test_fail "Expected git to track: $1"
}

assert_git_no_diffs() {
    # Error if there are staged changes (added, not yet commited):
    git diff --exit-code --staged || _test_fail "Unexpected staged changes"

    # Error if there are uncommited changes (to tracked files):
    git diff --exit-code || _test_fail "Unexpected uncommited changes"
}

# --- Assertions ---

assert_file_exists() {
    [ -e "$1" ] || _test_fail "Expected file to exist: $1"
}

assert_file_not_exists() {
    [ ! -e "$1" ] || _test_fail "Expected file to not exist: $1"
}

assert_file_contains() {
    grep -qF "$2" "$1" || _test_fail "Expected file '$1' to contain: $2"
}

assert_file_not_contains() {
    ! grep -qF "$2" "$1" || _test_fail "Expected file '$1' to NOT contain: $2"
}

assert_file_matches() {
    grep -qE "$2" "$1" || _test_fail "Expected file '$1' to match regex: $2"
}

assert_output_contains() {
    echo "$_LAST_OUTPUT" | grep -qF "$1" \
        || _test_fail "Expected output to contain: $1"
}

assert_output_not_contains() {
    ! echo "$_LAST_OUTPUT" | grep -qF "$1" \
        || _test_fail "Expected output to NOT contain: $1"
}

assert_success() {
    "$@" || _test_fail "Expected command to succeed: $*"
}

assert_failure() {
    local rc=0
    "$@" || rc=$?
    [ $rc -ne 0 ] || _test_fail "Expected command to fail: $*"
}

assert_equal() {
    [ "$1" = "$2" ] || _test_fail "Expected '$2' but got '$1'"
}

assert_not_equal() {
    [ "$1" != "$2" ] || _test_fail "Expected values to differ but both are: '$1'"
}

assert_diff() {
    diff "$1" "$2" || _test_fail "Files differ: $1 vs $2"
}

assert_no_diff() {
    ! diff -q "$1" "$2" > /dev/null 2>&1 \
        || _test_fail "Expected files to differ but they are identical: $1 vs $2"
}

assert_count() {
    local expected="$1" file="$2" pattern="$3"
    local actual
    actual=$(grep -cF "$pattern" "$file" || true)
    [ "$actual" -eq "$expected" ] \
        || _test_fail "Expected $expected occurrences of '$pattern' in '$file' but found $actual"
}

# --- Run / Capture ---

run() {
    local rc=0
    _LAST_OUTPUT=$("$@" 2>&1) || rc=$?
    _LAST_EXIT_CODE=$rc
    if [ $rc -ne 0 ]; then
        _test_fail "Command failed (exit $rc): $*"
    fi
}

run_expect_failure() {
    local rc=0
    _LAST_OUTPUT=$("$@" 2>&1) || rc=$?
    _LAST_EXIT_CODE=$rc
    if [ $rc -eq 0 ]; then
        _test_fail "Expected command to fail: $*"
    fi
}
