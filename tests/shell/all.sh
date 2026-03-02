#!/usr/bin/env bash
echo "Warning: These shell based tests use the cfbs you have installed"
echo "         If you haven't already, run: pip install ."
set -e
export CFBS_USER_AGENT=CI # this user agent will be excluded from the build modules statistics

_passed=0
_failed=0
_skipped=0
_total=0
_failures=""
_suite_start=$(date +%s)

run_test() {
    local test_script="$1"
    local test_name
    test_name=$(basename "$test_script" .sh)
    _total=$((_total + 1))

    local start end elapsed
    start=$(date +%s)

    local output
    local exit_code=0
    output=$(bash "$test_script" 2>&1) || exit_code=$?

    end=$(date +%s)
    elapsed=$((end - start))

    if [ $exit_code -eq 0 ]; then
        if echo "$output" | grep -q "^--- SKIP:"; then
            _skipped=$((_skipped + 1))
            echo "--- SKIP: $test_name (${elapsed}s)"
        else
            _passed=$((_passed + 1))
            echo "--- PASS: $test_name (${elapsed}s)"
        fi
    else
        _failed=$((_failed + 1))
        _failures="${_failures}  ${test_name}\n"
        echo "--- FAIL: $test_name (${elapsed}s)"
        echo "$output"
        echo "---"
    fi
}

run_test tests/shell/001_init.sh
run_test tests/shell/002_add.sh
run_test tests/shell/003_download.sh
run_test tests/shell/004_build.sh
run_test tests/shell/005_alias.sh
run_test tests/shell/006_search.sh
run_test tests/shell/007_install.sh
run_test tests/shell/008_remove.sh
run_test tests/shell/009_clean.sh
run_test tests/shell/010_local_add.sh
run_test tests/shell/011_update.sh
run_test tests/shell/012_prepend_dot_slash.sh
run_test tests/shell/013_add_url_commit.sh
run_test tests/shell/014_add_nonexistent.sh
run_test tests/shell/015_add_version.sh
run_test tests/shell/016_add_folders.sh
run_test tests/shell/017_info.sh
run_test tests/shell/018_update_input_one_variable.sh
run_test tests/shell/019_update_input_two_variables.sh
run_test tests/shell/020_update_input_list.sh
run_test tests/shell/021_update_input_list_with_keys.sh
run_test tests/shell/022_update_input_fail_variable.sh
run_test tests/shell/023_update_input_fail_number.sh
run_test tests/shell/024_update_input_fail_bundle.sh
run_test tests/shell/025_add_input_remove.sh
run_test tests/shell/026_init_no_masterfiles.sh
run_test tests/shell/027_init_masterfiles_version_master.sh
run_test tests/shell/028_init_masterfiles_version_3.18.2.sh
run_test tests/shell/029_init_masterfiles_version_3.18.1-1.sh
run_test tests/shell/030_get_set_input.sh
run_test tests/shell/031_get_set_input_pipe.sh
run_test tests/shell/032_set_input_unordered.sh
run_test tests/shell/033_add_commits_local_files.sh
run_test tests/shell/034_git_user_name_git_user_email.sh
run_test tests/shell/035_cfbs_build_compatibility_1.sh
run_test tests/shell/036_cfbs_build_compatibility_2.sh
run_test tests/shell/037_cfbs_validate.sh
run_test tests/shell/038_global_dir.sh
run_test tests/shell/039_add_added_by_field_update_1.sh
run_test tests/shell/040_add_added_by_field_update_2.sh
run_test tests/shell/041_add_multidep.sh
run_test tests/shell/042_update_from_url.sh
run_test tests/shell/043_replace_version.sh
run_test tests/shell/044_replace.sh
run_test tests/shell/045_update_from_url_branch_uptodate.sh
run_test tests/shell/046_update_from_url_branch.sh
run_test tests/shell/047_absolute_path_modules.sh

# Summary
_suite_end=$(date +%s)
_suite_elapsed=$((_suite_end - _suite_start))
echo ""
echo "=============================="
echo "Test Results: $_passed passed, $_failed failed, $_skipped skipped (total: $_total, ${_suite_elapsed}s)"
if [ $_failed -gt 0 ]; then
    echo ""
    echo "Failed tests:"
    echo -e "$_failures"
    exit 1
fi
echo "=============================="
echo "All cfbs shell tests completed successfully!"
