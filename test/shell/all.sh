echo "Warning: These shell based tests use the cfbs you have installed"
echo "         If you haven't already, run: pip install ."
set -e
set -x

bash test/shell/001_init.sh
bash test/shell/002_add.sh
bash test/shell/003_download.sh
bash test/shell/004_build.sh
bash test/shell/005_alias.sh
bash test/shell/006_search.sh
bash test/shell/007_install.sh
bash test/shell/008_remove.sh
bash test/shell/009_clean.sh
bash test/shell/010_local_add.sh
bash test/shell/011_update.sh
bash test/shell/012_prepend_dot_slash.sh
bash test/shell/013_add_url_commit.sh
bash test/shell/014_add_nonexistent.sh
bash test/shell/015_add_version.sh
bash test/shell/016_add_folders.sh
