echo "Warning: These shell based tests use the cfbs you have installed"
echo "         If you haven't already, run: pip install ."
set -e
set -x

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
