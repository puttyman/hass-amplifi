"""The Amplifi coordinator."""
import logging
import aiohttp
from async_timeout import timeout

from aiohttp.client_exceptions import ClientConnectorError
from datetime import timedelta

from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .client import AmplifiClient, AmplifiClientError

_LOGGER = logging.getLogger(__name__)

WIFI_DEVICES_IDX = 1
ETHERNET_PORTS_IDX = 4


class AmplifiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Amplifi data from router."""

    def __init__(self, hass, hostname, password):
        """Initialize."""
        self._hostname = hostname
        self._password = password
        self._wifi_devices = {}
        self._ethernet_ports = {}
        self._wan_speeds = {"download": 0, "upload": 0}
        self._router_mac_addr = None
        # Create jar for storing session cookies
        self._jar = aiohttp.CookieJar(unsafe=True)
        # Amplifi uses session cookie so we need a we client with a cookie jar
        self._client_sesssion = async_create_clientsession(
            hass, False, True, cookie_jar=self._jar
        )
        self._client = AmplifiClient(
            self._client_sesssion, self._hostname, self._password
        )

        # TODO: Make this a configurable value
        update_interval = timedelta(seconds=10)
        _LOGGER.debug("Data will be update every %s", update_interval)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        super().async_add_listener(self.extract_wifi_devices)
        super().async_add_listener(self.extract_ethernet_ports)
        super().async_add_listener(self.extract_wan_speeds)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            async with timeout(10):
                devices = await self._client.async_get_devices()
        except (AmplifiClientError, ClientConnectorError) as error:
            raise UpdateFailed(error) from error
        return devices

    def extract_wifi_devices(self):
        """Extract wifi devices from raw response after a successful update."""
        if self.data is None:
            return
        wifi_devices = {}
        raw_wifi_devices = self.data[WIFI_DEVICES_IDX]
        if raw_wifi_devices:
            for access_point in raw_wifi_devices:
                for wifi_band in raw_wifi_devices[access_point]:
                    for network_type in raw_wifi_devices[access_point][wifi_band]:
                        for macAddr in raw_wifi_devices[access_point][wifi_band][
                            network_type
                        ]:
                            device_info = raw_wifi_devices[access_point][wifi_band][
                                network_type
                            ][macAddr]
                            wifi_devices[macAddr] = device_info

        self._wifi_devices = wifi_devices

    def extract_ethernet_ports(self):
        if self.data is None:
            return
        router_mac_addr = self.get_router_mac_addr()
        self._ethernet_ports = self.data[ETHERNET_PORTS_IDX][router_mac_addr]

        _LOGGER.debug(f"ports={self.ethernet_ports}")

    def extract_wan_speeds(self):
        if self.data is None:
            return
        router_mac_addr = self.get_router_mac_addr()

        wan_port_data = self.data[ETHERNET_PORTS_IDX][router_mac_addr]["eth-0"]
        if "rx_bitrate" in wan_port_data:
            self._wan_speeds["download"] = (
                wan_port_data["rx_bitrate"] == 0
                if 0
                else wan_port_data["rx_bitrate"] / 1024
            )
        if "tx_bitrate" in wan_port_data and wan_port_data["tx_bitrate"] != 0:
            self._wan_speeds["upload"] = (
                wan_port_data["tx_bitrate"] == 0
                if 0
                else wan_port_data["tx_bitrate"] / 1024
            )

        _LOGGER.debug(f"wan_speeds={self._wan_speeds}")

    def find_router_mac_in_topology(self, topology_data):
        for k, v in topology_data.items():
            if k == "role" and v == "Router" and "mac" in topology_data:
                self._router_mac_addr = topology_data["mac"]
            elif isinstance(v, dict):
                self.find_router_mac_in_topology(v)
                

    def get_router_mac_addr(self):
        if self._router_mac_addr is None:
            self.find_router_mac_in_topology(self.data[0])

        return self._router_mac_addr

    def async_stop_refresh(self):
        super._async_stop_refresh()

    @property
    def wifi_devices(self):
        """Return the wifi devices."""
        return self._wifi_devices

    @property
    def ethernet_ports(self):
        """Return the ethernet ports."""
        return self._ethernet_ports

    @property
    def wan_speeds(self):
        """Return the wan speeds."""
        return self._wan_speeds
