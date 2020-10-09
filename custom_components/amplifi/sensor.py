"""Platform for sensor integration."""
import logging

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback

from .const import DOMAIN, COORDINATOR, COORDINATOR_LISTENER, ENTITIES

_LOGGER = logging.getLogger(__name__)
WIFI_DEVICES_IDX = 1


def get_router_mac_addr(self, devices):
    for device in devices[0]:
        if devices[0][device]["role"] == "Router":
            return device


def get_wan_port_info(self, devices):
    router_mac_addr = self.get_router_mac_addr(devices)
    wan_port = devices[4][router_mac_addr]["eth-0"]
    return wan_port


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    @callback
    def async_discover_sensor():
        """Discover and add a discovered sensor."""
        amplifi_devices = {}
        wifi_devices = coordinator.data[WIFI_DEVICES_IDX]
        if wifi_devices:
            for access_point in wifi_devices:
                for wifi_band in wifi_devices[access_point]:
                    for network_type in wifi_devices[access_point][wifi_band]:
                        for macAddr in wifi_devices[access_point][wifi_band][
                            network_type
                        ]:
                            device_info = wifi_devices[access_point][wifi_band][
                                network_type
                            ][macAddr]
                            amplifi_devices[macAddr] = device_info

        for macAddr in amplifi_devices:
            if macAddr not in hass.data[DOMAIN][config_entry.entry_id][ENTITIES]:
                async_add_entities(
                    [
                        AmplifiDeviceSensor(
                            coordinator, macAddr, amplifi_devices[macAddr], config_entry
                        )
                    ]
                )

    hass.data[DOMAIN][config_entry.entry_id][
        COORDINATOR_LISTENER
    ] = async_discover_sensor

    async_discover_sensor()

    coordinator.async_add_listener(async_discover_sensor)


class AmplifiDeviceSensor(CoordinatorEntity):
    """Sensor representing a device connected to amplifi."""

    name = None
    unique_id = None
    data = None
    connected = True

    def __init__(self, coordinator, macAddr, initial_data, config_entry):
        """Initialize amplifi sensor."""
        super().__init__(coordinator)
        self.data = initial_data
        self.unique_id = macAddr
        self.config_entry = config_entry
        self.connected = True

        if self.data is not None and "Description" in self.data:
            self.name = f"{DOMAIN}_{self.data['Description']}"
        elif self.data is not None and "HostName" in self.data:
            self.name = f"{DOMAIN}_{self.data['HostName']}"
        elif self.data is not None and "Address" in self.data:
            self.name = f"{DOMAIN}_{self.data['Address']}"
        else:
            self.name = macAddr

    @property
    def available(self):
        """Return if sensor is available."""
        # Sensor is available as long we have connectivity to the router
        return self.coordinator.last_update_success

    @property
    def state(self):
        """State of the sensor."""
        return "connected" if self.connected else "disconnected"

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:devices"

    @property
    def device_state_attributes(self):
        """Return device attributes."""
        if self.coordinator.last_update_success and self.data is not None:
            return self.data

    def update(self):
        _LOGGER.debug(f"entity={self.unique_id} update() was called")
        self._handle_coordinator_update()

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        entities = self.hass.data[DOMAIN][self.config_entry.entry_id][ENTITIES]
        entities[self.unique_id] = self.unique_id
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        entities = self.hass.data[DOMAIN][self.config_entry.entry_id][ENTITIES]
        entities.pop(self.unique_id)
        self.coordinator.async_remove_listener(self._handle_coordinator_update)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self):
        wifi_devices = self.coordinator.data[WIFI_DEVICES_IDX]
        self.connected = False
        if wifi_devices:
            for access_point in wifi_devices:
                for wifi_band in wifi_devices[access_point]:
                    for network_type in wifi_devices[access_point][wifi_band]:
                        for device in wifi_devices[access_point][wifi_band][
                            network_type
                        ]:
                            if self.unique_id == device:
                                self.data = wifi_devices[access_point][wifi_band][
                                    network_type
                                ][device]
                                self.connected = True
        _LOGGER.debug(
            f"entity={self.unique_id} was updated via _handle_coordinator_update"
        )
        self.async_write_ha_state()
        # May need to handle this differently in future versions of hass
        # super()._handle_coordinator_update()