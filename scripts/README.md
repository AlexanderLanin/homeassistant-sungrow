# Scripts

## How to run scripts (pipx)

**DOES NOT WORK YET**

The scripts (notably `dump.py`) are compatible with pipx.

If you don't have pipx installed, install it first as described in [pipx documentation](https://pipxproject.github.io/pipx/installation/).

Then run:

```bash
pipx install git+https://github.com/AlexanderLanin/homeassistant-sungrow@temp
pipx run sungrow_dump
```

## How to run scripts (poetry)

**SEEMS TO WORK**

The scripts (notably `dump.py`) are compatible with poetry.

If you don't have poetry installed, install it first as described in [poetry documentation](https://python-poetry.org/docs/#installation).

Then run:

```bash
git clone --branch temp https://github.com/AlexanderLanin/homeassistant-sungrow.git
cd homeassistant-sungrow
poetry install
poetry run sungrow_dump
```
