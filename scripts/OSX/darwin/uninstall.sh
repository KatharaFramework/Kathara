#!/bin/bash

# Check running user
if (( $EUID != 0 )); then
    echo "Please run as root."
    exit
fi

echo "Welcome to Kathara Uninstaller"
echo "Kathara will be REMOVED!"

while true; do
    read -p "Do you wish to continue [Y/n]? " answer
    [[ $answer == "y" || $answer == "Y" || $answer == "" ]] && break
    [[ $answer == "n" || $answer == "N" ]] && exit 0
    echo "Please answer with 'y' or 'n'"
done

echo "Application uninstalling process started"

# remove running containers
/Library/Kathara/kathara wipe -a -f
if [ $? -eq 0 ]
then
  echo "[1/5] [DONE] Successfully deleted all running Kathara devices"
else
  echo "[1/5] [ERROR] Could not delete all running Kathara devices" >&2
fi

# remove link to shorcut file
find "/usr/local/bin/" -name "kathara" | xargs rm
if [ $? -eq 0 ]
then
  echo "[2/5] [DONE] Successfully deleted shortcut links"
else
  echo "[2/5] [ERROR] Could not delete shortcut links" >&2
fi

# forget from pkgutil
pkgutil --forget "org.kathara.kathara" > /dev/null 2>&1
if [ $? -eq 0 ]
then
  echo "[3/5] [DONE] Successfully deleted application informations"
else
  echo "[3/5] [ERROR] Could not delete application informations" >&2
fi

__MANPAGES__
echo "[4/5] [DONE] Successfully deleted man pages."


# remove application source distribution
[ -e "/Library/Kathara" ] && rm -rf "/Library/Kathara"
if [ $? -eq 0 ]
then
  echo "[5/5] [DONE] Successfully deleted application"
else
  echo "[5/5] [ERROR] Could not delete application" >&2
fi

echo "Application uninstall process finished"
exit 0
