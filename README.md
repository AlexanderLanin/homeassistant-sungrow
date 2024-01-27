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

For many things you can open this repository within a Codespace, but if you want access to your local inverter or home assistant you need to clone this repository.


### Development without docker
This is poorly maintained, but it should work in general:
* In case you don't have it, you can install poetry via `curl -sSL https://install.python-poetry.org | python3 -` or some other method as described on https://python-poetry.org/docs/#installing-with-the-official-installer
* Then you need to run `poetry install` and it will install everything you need for development.
* Run `poetry shell` to switch to that virtual environment where all dependencies are available.
* Have a look at the extensions and settings listed in `.devcontainer/decontainer.json`
