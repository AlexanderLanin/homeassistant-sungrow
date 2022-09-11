# Sungrow Inverter add-on for Home Assistant

## Installation

### Home Assistant OS

```bash
ssh root@homeassistant.local
git clone --depth 1 https://github.com/alangibson/homeassistant-sungrow.git
mkdir -p /config/custom_components
mv homeassistant-sungrow/custom_components/sungrow /config/custom_components/
reboot
```
