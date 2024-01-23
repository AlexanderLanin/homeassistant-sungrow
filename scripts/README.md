# Scripts

## How to run scripts (pipx)

The scripts (notably `dump.py`) are compatible with pipx.

This method will not pollute your system with packages as pipx creates a virtual environment for the project.
Actually you don't even need python installed, let alone the correct version!

If you don't have pipx installed, install it first as described in [pipx documentation](https://pipxproject.github.io/pipx/installation/).

Then run:

```bash
pipx run --spec git+https://github.com/AlexanderLanin/homeassistant-sungrow@temp sungrow_dump YOUR_INVERTER_IP ANOTHER_INVERTER_IP ...

# for updating, just tell pipx to redownload:
pipx run --no-cache --spec git+https://github.com/AlexanderLanin/homeassistant-sungrow@temp sungrow_dump YOUR_INVERTER_IP ANOTHER_INVERTER_IP ...
```

## How to run scripts (poetry)

The scripts (notably `dump.py`) are compatible with poetry.

This method will not pollute your system with packages as poetry creates a virtual environment for the project.

If you don't have poetry installed, install it first as described in [poetry documentation](https://python-poetry.org/docs/#installation).

Then run:

```bash
git clone --branch temp https://github.com/AlexanderLanin/homeassistant-sungrow.git
cd homeassistant-sungrow
poetry install
poetry run sungrow_dump YOUR_INVERTER_IP ANOTHER_INVERTER_IP ...
```
