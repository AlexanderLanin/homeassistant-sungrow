# Sungrow inverter integration for Home Assistant

## Known limitations
* Only tested with SH8.0RT-20
* Early alpha, expect bugs!

Next steps:
* [ ] Add tests
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
- [Sungrow inverter integration for Home Assistant](https://github.com/alangibson/homeassistant-sungrow/) by [Alan Gibson](https://github.com/alangibson) (we might merge our efforts)
- [SunGather](https://github.com/bohdan-s/SunGather/tree/main) is a Home Assistant Add-On for gathering data from Sungrow inverters by [Bohdan Shtepan](https://github.com/bohdan-s)

Planned, but not yet considered:
- [An easy-to-use YAML-based integration for several Sungrow inverters for Home Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant) by [Michael Kaiser](https://github.com/mkaiser)

## License

To be determined... Apache 2.0? MIT? GPL?

## Development

No proper documentation yet, but here are some pointers:
* See https://github.com/alangibson/homeassistant-sungrow/issues/14
* In case tests don't show up in VS Code: https://github.com/microsoft/vscode-python/issues/22383
* Don't use GitHub Codespaces if you want to connect to your inverter ;-)
