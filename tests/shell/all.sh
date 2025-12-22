echo "Warning: These shell based tests use the cfbs you have installed"
echo "         If you haven't already, run: pip install ."
set -e
set -x
export CFBS_USER_AGENT=CI # this user agent will be excluded from the build modules statistics

bash tests/shell/001_init.sh
bash tests/shell/002_add.sh
bash tests/shell/003_download.sh
bash tests/shell/004_build.sh
bash tests/shell/005_alias.sh
bash tests/shell/006_search.sh
bash tests/shell/007_install.sh
bash tests/shell/008_remove.sh
bash tests/shell/009_clean.sh
bash tests/shell/010_local_add.sh
bash tests/shell/011_update.sh
bash tests/shell/012_prepend_dot_slash.sh
bash tests/shell/013_add_url_commit.sh
bash tests/shell/014_add_nonexistent.sh
bash tests/shell/015_add_version.sh
bash tests/shell/016_add_folders.sh
bash tests/shell/017_info.sh
bash tests/shell/018_update_input_one_variable.sh
bash tests/shell/019_update_input_two_variables.sh
bash tests/shell/020_update_input_list.sh
bash tests/shell/021_update_input_list_with_keys.sh
bash tests/shell/022_update_input_fail_variable.sh
bash tests/shell/023_update_input_fail_number.sh
bash tests/shell/024_update_input_fail_bundle.sh
bash tests/shell/025_add_input_remove.sh
bash tests/shell/026_init_no_masterfiles.sh
bash tests/shell/027_init_masterfiles_version_master.sh
bash tests/shell/028_init_masterfiles_version_3.18.2.sh
bash tests/shell/029_init_masterfiles_version_3.18.1-1.sh
bash tests/shell/030_get_set_input.sh
bash tests/shell/031_get_set_input_pipe.sh
bash tests/shell/032_set_input_unordered.sh
bash tests/shell/033_add_commits_local_files.sh
bash tests/shell/034_git_user_name_git_user_email.sh
bash tests/shell/035_cfbs_build_compatibility_1.sh
bash tests/shell/036_cfbs_build_compatibility_2.sh
bash tests/shell/037_cfbs_validate.sh
bash tests/shell/038_global_dir.sh
bash tests/shell/039_add_added_by_field_update_1.sh
bash tests/shell/040_add_added_by_field_update_2.sh
bash tests/shell/041_add_multidep.sh
bash tests/shell/042_update_from_url.sh
bash tests/shell/043_replace_version.sh
bash tests/shell/044_replace.sh
bash tests/shell/045_update_from_url_branch_uptodate.sh
bash tests/shell/046_update_from_url_branch.sh
bash tests/shell/047_absolute_path_modules.sh

echo "All cfbs shell tests completed successfully!"
