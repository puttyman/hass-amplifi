"""Platform for device_tracker integration."""
import re
import logging

from datetime import datetime
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.core import callback
from .const import DOMAIN, COORDINATOR, COORDINATOR_LISTENER, ENTITIES
from .coordinator import AmplifiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
ETHERNET_PORTS = 5


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""

    coordinator: AmplifiDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ][COORDINATOR]

    @callback
    def async_discover_device_tracker():
        """Discover and add a discovered device_tracker."""
        for mac_addr in coordinator.wifi_devices:
            if mac_addr not in hass.data[DOMAIN][config_entry.entry_id][ENTITIES]:
                async_add_entities(
                    [
                        AmplifiWifiDeviceTracker(
                            coordinator,
                            mac_addr,
                            config_entry,
                        )
                    ]
                )

        for port in range(0, 5):
            port_unique_id = f"{DOMAIN}_eth_port_{port}"
            if port_unique_id not in hass.data[DOMAIN][config_entry.entry_id][ENTITIES]:
                async_add_entities(
                    [
                        AmplifiEthernetDeviceTracker(
                            coordinator,
                            port,
                            config_entry,
                        )
                    ]
                )

    @callback
    def async_unsub_discover_device_tracker():
        """Stop discovery when config entry is removed."""
        coordinator.async_remove_listener(async_discover_device_tracker)

    async_discover_device_tracker()

    coordinator.async_add_listener(async_discover_device_tracker)
    config_entry.async_on_unload(async_unsub_discover_device_tracker)


class AmplifiWifiDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Representing a wireless device connected to amplifi."""

    _name = None
    _data = None
    _connected = True
    unique_id = None

    def __init__(
        self, coordinator: AmplifiDataUpdateCoordinator, mac_addr, config_entry
    ):
        """Initialize amplifi wireless device tracker."""
        super().__init__(coordinator)
        self.unique_id = mac_addr
        self._data = coordinator.wifi_devices[mac_addr]
        self.config_entry = config_entry
        self._connected = True

        if self._data is not None and "Description" in self._data:
            self._name = f"{DOMAIN}_{self._data['Description']}"
        elif self._data is not None and "HostName" in self._data:
            self._name = f"{DOMAIN}_{self._data['HostName']}"
        elif self._data is not None and "Address" in self._data:
            self._name = f"{DOMAIN}_{self._data['Address']}"
        else:
            self._name = self.unique_id

        self._name = re.sub("[^0-9a-zA-Z]+", "_", self._name).lower()

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SOURCE_TYPE_ROUTER

    @property
    def is_connected(self):
        return self._connected

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:devices"

    @property
    def ip_address(self):
        """Return the primary ip address of the device."""
        if "Address" in self._data:
            return self._data["Address"]

        return None

    @property
    def mac_address(self):
        """Return the mac address of the device."""
        return self.unique_id

    @property
    def hostname(self):
        """Return hostname of the device."""
        if "HostName" in self._data:
            return self._data["HostName"]

        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self.coordinator.last_update_success and self._data is not None:
            return {**self._data, "last_seen": datetime.now().isoformat()}
        return {}

    def update(self):
        _LOGGER.debug(f"entity={self.unique_id} update() was called")
        self._handle_coordinator_update()

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        entities = self.hass.data[DOMAIN][self.config_entry.entry_id][ENTITIES]
        entities[self.unique_id] = self.unique_id
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        entities = self.hass.data[DOMAIN][self.config_entry.entry_id][ENTITIES]
        entities.pop(self.unique_id)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self):
        self._connected = False

        if self.unique_id in self.coordinator.wifi_devices:
            self._data = self.coordinator.wifi_devices[self.unique_id]
            self._connected = True

        _LOGGER.debug(
            f"entity={self.unique_id} was updated via _handle_coordinator_update"
        )

        super()._handle_coordinator_update()


class AmplifiEthernetDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Representing an ethernet port of amplifi."""

    _name = None
    _data = {}
    _connected = True
    _is_wan = False
    unique_id = None

    def __init__(self, coordinator: AmplifiDataUpdateCoordinator, port, config_entry):
        """Initialize amplifi ethernet device tracker."""
        super().__init__(coordinator)
        self._port = port
        self._data_key = f"eth-{port}"
        self.unique_id = f"{DOMAIN}_eth_port_{self._port}"
        self._data = coordinator.ethernet_ports[f"{self._data_key}"]
        self.config_entry = config_entry

    @property
    def name(self):
        """Return the name."""
        return self.unique_id

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SOURCE_TYPE_ROUTER

    @property
    def is_connected(self):
        return "link" in self._data and self._data["link"] == True

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:ethernet"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self.coordinator.last_update_success and self._data is not None:
            return {**self._data, "last_seen": datetime.now().isoformat()}
        return {}

    def update(self):
        _LOGGER.debug(f"entity={self.unique_id} update() was called")
        self._handle_coordinator_update()

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        entities = self.hass.data[DOMAIN][self.config_entry.entry_id][ENTITIES]
        entities[self.unique_id] = self.unique_id
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        entities = self.hass.data[DOMAIN][self.config_entry.entry_id][ENTITIES]
        entities.pop(self.unique_id)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self):
        if self._data_key in self.coordinator.ethernet_ports:
            self._data = self.coordinator.ethernet_ports[self._data_key]

        _LOGGER.debug(
            f"entity={self.unique_id} was updated via _handle_coordinator_update"
        )
        super()._handle_coordinator_update()
