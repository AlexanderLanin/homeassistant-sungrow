# Sungrow inverter integration for Home Assistant

## Known limitations
* Only tested with SH8.0RT-20
* Works only with internal LAN port (not via WiNet-S etc)
* Early alpha, expect bugs!

Next steps:
* [ ] Add more tests
* [ ] Add CI/CD
* [ ] Add ability to report issues (with data attached)

## Installation

This guide assumes you already have HACS installed.
* If you don't have HACS installed, you need to [install](https://hacs.xyz/docs/setup/download) and [configure](https://hacs.xyz/docs/configuration/basic) it first.
* Add custom repository repo in HACS (see [HACS documentation](https://hacs.xyz/docs/faq/custom_repositories/) for more details)
  * Repository: https://github.com/AlexanderLanin/homeassistant-sungrow
  * Category: Integration
* Download the Integration in HACS
* Restart Home Assistant

* Add the Sungrow integration in the HA Devices and Services menu
* When prompted, enter the IP address or hostname of your inverter.

  You can probably leave everything else at the defaults

### Installation without Home Assistant

In order to try this integration without Home Assistant, you can use the following command:

*NOT SUPPORTED YET*

```bash
pipx install git+https://github.com/AlexanderLanin/homeassistant-sungrow.git
...
```

## Configuration

Go to Configuration -> Integrations -> Sungrow Inverter -> Select your inverter -> Configure

## Credits

This integration stands on the shoulders of giants:
- [An easy-to-use YAML-based integration for several Sungrow inverters for Home Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant) by [Martin Kaiser](https://github.com/mkaiser)
- [SunGather](https://github.com/bohdan-s/SunGather/tree/main) is a Home Assistant Add-On for gathering data from Sungrow inverters by [Bohdan Shtepan](https://github.com/bohdan-s)

The idea to create a custom integration came from:
- [Sungrow inverter integration for Home Assistant](https://github.com/alangibson/homeassistant-sungrow/) by [Alan Gibson](https://github.com/alangibson)

## License

To be determined... Apache 2.0? MIT? GPL?

## Development

No proper documentation yet, but here are some pointers:
* See https://github.com/alangibson/homeassistant-sungrow/issues/14
* In case tests don't show up in VS Code: https://github.com/microsoft/vscode-python/issues/22383
* Don't use GitHub Codespaces if you want to connect to your inverter ;-)

### Poetry

This project is using poetry for dependency management.
The author has no experience with poetry, so please bear with me.

To install poetry, see https://python-poetry.org/docs/#installation

To install dependencies, run `poetry install`

To run tests, run `poetry run pytest`.

Alternatively, you can run `poetry shell` to activate the virtual environment and then run `pytest`.

Run `poertry lock` to update the lock file.
