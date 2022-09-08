#!/bin/bash
set -euo pipefail

echo "Running code analysis..."
ruff .
mypy .


echo "Copying files to home assistant..."

# ToDo: skip __pycache__ folders
# See e.g. https://stackoverflow.com/questions/15121337/recursively-use-scp-but-excluding-some-folders
rm -rf custom_components/sungrow/__pycache__
rm -rf custom_components/sungrow/core/__pycache__

scp -r custom_components/sungrow/ root@homeassistant.local:/root/homeassistant/custom_components || {
  echo "Error: Failed to copy files."
  echo "* Do you have ssh addon running in home assistant?"
  echo "* Did you configure it for remote access?"
  echo "* Did you add your ssh key to the authorized_keys? (run: eval `ssh-agent` and ssh- ssh-add)"
  echo "* Can you connect via ssh? (run: ssh root@homeassistant.local)"
  exit 1
}


echo "Restarting home assistant..."
ssh root@homeassistant.local "ha core restart"


echo "Tailing log... Press Ctrl+C to exit."
# ToDo: check if configuration.yaml has sungrow section:
# logger:
#   default: warning
#   logs:
#     custom_components.sungrow: debug
ssh root@homeassistant.local "tail -f /root/homeassistant/home-assistant.log"
