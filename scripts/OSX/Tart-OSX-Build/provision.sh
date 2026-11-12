#!/bin/bash
set -euo pipefail

PYTHON_VERSION="3.13.12"

eval "$(/opt/homebrew/bin/brew shellenv)"

# Install Rosetta 2
sudo softwareupdate --install-rosetta --agree-to-license

# Install Python Universal
curl -fsSL -o /tmp/python.pkg "https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macos11.pkg"
sudo installer -pkg /tmp/python.pkg -target /
rm -f /tmp/python.pkg

# Install ronn-ng for man pages
rbenv exec gem install ronn-ng
rbenv rehash

# Add paths to the zsh profile
cat >> ~/.zprofile <<EOF
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:\$PATH"
export RUBYOPT="-KU -E utf-8:utf-8"
EOF

# Flush changes to disk
sync