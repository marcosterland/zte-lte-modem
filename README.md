# ZTE LTE Modem

Home Assistant custom integration for ZTE MF79U-style USB LTE modems (goform HTTP API).

## Installation

Add this repository in [HACS](https://hacs.xyz/) as a custom repository, then install **ZTE LTE Modem**.

Or copy `custom_components/zte_modem` into your Home Assistant `config/custom_components/` folder.

## Configuration

1. Open **Settings → Devices & services → Add integration**.
2. Search for **ZTE LTE Modem**.
3. Enter the modem web UI host (default `192.168.0.1`) and password (default `admin`).

## Features

- Signal and LTE metrics (RSRP, RSRQ, RSSI, SNR, signal bars)
- Network status, provider, band, cell ID, WAN IP, PPP status
- Traffic rates and monthly byte counters
- Battery percentage (if reported by the modem)
- SMS inbox summary sensor
- Reboot button and mobile data switch

## Requirements

- ZTE modem with MF79U-style login (base64 password on `/goform/goform_set_cmd_process`).
- Home Assistant 2024.6 or newer.

## Credits

Modem API patterns from [an1by/ZTEModemAPI](https://github.com/an1by/ZTEModemAPI).
