"""Constants for the ZTE LTE Modem integration."""

DOMAIN = "zte_modem"

DEFAULT_HOST = "192.168.0.1"
DEFAULT_PASSWORD = "admin"

UPDATE_INTERVAL_SECONDS = 30

CONF_HOST = "host"
CONF_PASSWORD = "password"

GOFORM_SET = "/goform/goform_set_cmd_process"
GOFORM_GET = "/goform/goform_get_cmd_process"

GOFORM_LOGIN = "LOGIN"
GOFORM_REBOOT = "REBOOT_DEVICE"
GOFORM_CONNECT = "CONNECT_NETWORK"
GOFORM_DISCONNECT = "DISCONNECT_NETWORK"

PPP_CONNECTED = "ppp_connected"

POLL_FIELDS = (
    "lte_rsrp",
    "lte_rsrq",
    "lte_rssi",
    "lte_snr",
    "signalbar",
    "network_type",
    "network_provider",
    "wan_active_band",
    "cell_id",
    "lte_pci",
    "wan_ipaddr",
    "ppp_status",
    "simcard_roam",
    "realtime_rx_thrpt",
    "realtime_tx_thrpt",
    "monthly_rx_bytes",
    "monthly_tx_bytes",
    "battery_vol_percent",
    "sim_iccid",
    "imei",
    "hardware_version",
    "wa_inner_version",
)

SMS_LIMIT = 20
