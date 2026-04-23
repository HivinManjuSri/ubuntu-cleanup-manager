# Ubuntu Cleanup Manager

Ubuntu Cleanup Manager is a PyQt5 desktop utility for Ubuntu systems. It gives you a simple graphical interface to:

- view Ubuntu version and repository status
- check upgradeable packages
- run `apt update`
- run `apt autoclean`
- run `apt clean`
- run `apt autoremove`
- review action logs inside the app

## Features

- Styled desktop interface
- Background execution for long-running package actions
- App launcher integration
- Log file support
- Debian package build script included

## Requirements

For source execution:

- Ubuntu 19.04 or newer
- Python 3
- `python3-pyqt5`
- `policykit-1`

Install the required packages:

```bash
sudo apt update
sudo apt install -y python3 python3-pyqt5 policykit-1