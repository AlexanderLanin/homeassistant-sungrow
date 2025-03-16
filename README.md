# Sungrow inverter integration for Home Assistant

## Current state

This project was abandoned for more than a year. I'm currently picking it up again. I'm trying to get it to work with the latest Home Assistant version. I also need to check whether it's still relevant, as there may be other integrations available now...

## Known limitations
* :warning: It's not working :warning:
* Only tested with SH8.0RT-20
* Only tested with one home assistant version
* Early alpha, expect bugs!


## Installation

This guide assumes you already have HACS installed.
* If you don't have HACS installed, you need to [install](https://hacs.xyz/docs/use/download/download/) and [configure](https://hacs.xyz/docs/use/configuration/basic/) it first.
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

This integration itself stands on the shoulders of giants:
- [An easy-to-use YAML-based integration for several Sungrow inverters for Home Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant) by [Martin Kaiser](https://github.com/mkaiser)
- [SunGather](https://github.com/bohdan-s/SunGather/tree/main) is a Home Assistant Add-On for gathering data from Sungrow inverters by [Bohdan Shtepan](https://github.com/bohdan-s)

The idea to create a custom integration came from:
- [Sungrow inverter integration for Home Assistant](https://github.com/alangibson/homeassistant-sungrow/) by [Alan Gibson](https://github.com/alangibson)

However, no code was taken from these projects. Not because they are bad in any way, but because I wanted to learn how to create a custom integration for Home Assistant. This project is a learning experience for me.

## License

The current license is *CC BY-NC 4.0*. I'll very likely change it in the future, but for now I want to keep it simple. The reason for this is that I don't want to see this integration being used in a commercial product. If you want to use it in a commercial product, please contact me first.

## Development

For many things you can open this repository within a Codespace, but if you want access to your local inverter or home assistant you need to clone this repository.
Best supported method is to use the devcontainer, which is a docker container with all the necessary tools and dependencies.
(Use the "Reopen in Container" button in the lower right corner of VS Code)

To get the virtual environment running, you may need to run `uv sync` in the terminal. This will create a virtual environment and install all the dependencies.

### Development without docker
This is poorly maintained, but it should work in general:
* Install uv
* TODO: Add more instructions

### Run the local version

* Run `scripts/update_ha.sh` to deploy the current version to your home assistant instance.
