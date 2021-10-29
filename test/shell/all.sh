echo "Warning: These shell based tests use the cfbs you have installed"
echo "         If you haven't already, run: pip install ."
set -e
set -x

bash test/shell/001_init.sh
bash test/shell/002_add.sh
