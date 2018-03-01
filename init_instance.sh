#!/bin/bash

clone_dir=nocaptcha

github_key="
"

log()
{
  echo "$*" >&2
  # TODO: use logger?
}

setup_ubuntu() {
  sl_fn=/etc/apt/sources.list
  grep -Fq 'old-releases.ubuntu.com' $sl_fn || {
    # First need to upgrade the sources.list file to use old-releases
    log "Updating $sl_fn"
    sudo sed -i -re 's#http://.*\.archive\.ubuntu\.com|http://security\.ubuntu\.com#http://old-releases.ubuntu.com#g' $sl_fn
  }

  yes | {
    # python-xlib for pyautogui
    sudo apt-get update && sudo apt-get dist-upgrade
    # Python stuff for pip
    sudo apt-get install python3-venv #python3-xlib
    # General X stuff
    sudo apt-get install firefox #ubuntu-desktop tightvncserver gnome-panel gnome-settings-daemon
  } 2>apt.log 1>&2
}

setup_arch() {
  # Everything is done in init_arch_1.sh
  :
}

if [ -f /etc/debian_version ]; then
  setup_ubuntu
elif [ -f /etc/arch-release ]; then
  setup_arch
else
  log 'Unsupported OS release'
  exit 1
fi

key_fn=~/github.key
[ -f $key_fn ] || {
  echo "$github_key" > $key_fn
  chmod 400 $key_fn
}

export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -i $key_fn"
if [ -d "$clone_dir" ]; then
  log "Updating"
  (cd $clone_dir; git pull)
else
  : #git clone git@gitlab.com:zerho/loose-ocelot/linux-simulator.git "$clone_dir" -b development
fi

if [ ! -d venv ]; then
  log "Creating venv"
  python3 -m venv venv
  . venv/bin/activate
  pip install -U pip
  log "Installing packages"
  #pip installpython3-xlib # This one needs to finish completely for pyautogui
  pip install flask boto3 selenium #pyautogui keyboard retrying
fi

# TODO: copy aws credentials
# .aws_credentials



