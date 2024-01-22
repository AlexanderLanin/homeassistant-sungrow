# Scripts

## How to run scripts without cloning the repository

**THIS DOES NOT WORK YET. IT'S JUST AN IDEA.**

The scripts (notably `dump.py`) are compatible with pipx.

To install pipx, run the following command. This should be fine without virtualenv.

```bash
python3 -m pip install pipx
```

You can now run the scripts without further worries:

```bash
pipx install git+https://github.com/AlexanderLanin/homeassistant-sungrow@temp
pipx run sungrow_dump
```
