set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
rm -rf ./*

# Try to be nice to the user - back up and restore their
# module cache (~/.cfengine/cfbs/downloads):

cleanup_restore_backup()
{
  if [ -d ~/.cfengine/cfbs_backup ]; then
    if [ -d ~/.cfengine/cfbs ]; then
      # Should be okay to delete this - it's created by a bug in cfbs or this test
      # the "real" data we care about is in downloads_backup
      rm -rf ~/.cfengine/cfbs
    fi
    echo "Restoring backup"
    mv ~/.cfengine/cfbs_backup ~/.cfengine/cfbs
  fi
}

if [ -d ~/.cfengine/cfbs ]; then # Global dir used by cfbs by default
  if [ -d ~/.cfengine/cfbs_backup ]; then # Backup dir used by this test
    echo "Warning: Removing previous backup in" ~/.cfengine/cfbs_backup
    rm -rf ~/.cfengine/cfbs_backup
  fi
  # Setting the trap here, after determining that we need to backup and
  # after potentially deleting an older backup, so we don't end up
  # restoring a backup which was not created in this test run:
  trap cleanup_restore_backup EXIT ERR SIGHUP SIGINT SIGQUIT SIGABRT
  mv ~/.cfengine/cfbs ~/.cfengine/cfbs_backup
fi

test ! -e ./out/cfbs_global/
test ! -e ~/.cfengine/cfbs

# CFBS_GLOBAL_DIR allows us to override ~/.cfengine/cfbs with
# another path, for example for situations where you want to run
# cfbs as root, but not having access to root's home directory:
CFBS_GLOBAL_DIR="./out/cfbs_global" cfbs --non-interactive init
CFBS_GLOBAL_DIR="./out/cfbs_global" cfbs download

# Check that something was downloaded in the correct place:
ls ./out/cfbs_global/downloads/github.com/cfengine/masterfiles/*
# And nothing was downloaded or created in the wrong place:
test ! -e ~/.cfengine/cfbs

# Test some other commands, just in case:
rm -rf "./out/cfbs_global"
CFBS_GLOBAL_DIR="./out/cfbs_global" cfbs status
CFBS_GLOBAL_DIR="./out/cfbs_global" cfbs download
CFBS_GLOBAL_DIR="./out/cfbs_global" cfbs build

# Same checks as above:
ls ./out/cfbs_global/downloads/github.com/cfengine/masterfiles/*
test ! -e ~/.cfengine/cfbs
