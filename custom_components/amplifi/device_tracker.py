"""Platform for device_tracker integration."""
import re
import logging

from datetime import datetime
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker import SourceType
from homeassistant.core import callback
from .const import DOMAIN, COORDINATOR, COORDINATOR_LISTENER, ENTITIES, CONF_ENABLE_NEW_DEVICES
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

        is_device = False
        for port in range(0, 5):
            port_unique_id = f"{DOMAIN}_eth_port_{port}"
            if port_unique_id not in hass.data[DOMAIN][config_entry.entry_id][ENTITIES]:
                async_add_entities(
                    [
                        AmplifiEthernetDeviceTracker(
                            coordinator,
                            port,
                            config_entry,
                            is_device,
                        )
                    ]
                )

        is_device = True
        for mac_addr in coordinator.ethernet_devices:
            if mac_addr not in hass.data[DOMAIN][config_entry.entry_id][ENTITIES]:
                async_add_entities(
                    [
                        AmplifiEthernetDeviceTracker(
                            coordinator,
                            mac_addr,
                            config_entry,
                            is_device,
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
    _description = None
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
            self._description = self._data['Description']
        elif self._data is not None and "HostName" in self._data:
            self._name = f"{DOMAIN}_{self._data['HostName']}"
            self._description = self._data['HostName']
        elif self._data is not None and "Address" in self._data:
            self._name = f"{DOMAIN}_{self._data['Address']}"
            self._description = self._data['Address']
        else:
            self._name = f"{DOMAIN}_{self.unique_id}"

        self._name = re.sub("[^0-9a-zA-Z]+", "_", self._name).lower()
        # Override the entity_id so we can provide a better friendly name
        self.entity_id = f'device_tracker.{self._name}'

    @property
    def name(self):
        """Return the friendly name."""
        if self._description is not None:
            return self._description
        else:
            return self._name

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SourceType.ROUTER

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
    def connected_to(self):
        """Return mac address of the AP this device is connected to."""
        if "connected_to" in self._data:
            return self._data["connected_to"]

        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self.coordinator.last_update_success and self._data is not None:
            return {**self._data, "last_seen": datetime.now().isoformat()}
        return {}

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        if self.config_entry.data.get(CONF_ENABLE_NEW_DEVICES, False):
            return True
        
        return False

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
    _description = None
    _data = {}
    _device_info = {}
    _connected = True
    _is_wan = False
    _is_device = False
    unique_id = None

    def __init__(self, coordinator: AmplifiDataUpdateCoordinator, identifier, config_entry, is_device):
        """Initialize amplifi ethernet device tracker."""
        super().__init__(coordinator)
        if is_device:
            self._mac_addr = identifier
            self._data_key = self._mac_addr
            self.unique_id = self._mac_addr
            self._data = coordinator.ethernet_devices[f"{self._data_key}"]
            self.config_entry = config_entry

            # Optional device info for connected Ethernet ports
            if self._mac_addr in coordinator.ethernet_devices:
                self._device_info = coordinator.ethernet_devices[self._mac_addr]

            if self._device_info is not None and "description" in self._device_info:
                self._name = f"{DOMAIN}_{self._data['description']}"
                self._description = self._device_info['description']
            elif self._device_info is not None and "host_name" in self._device_info:
                self._name = f"{DOMAIN}_{self._data['host_name']}"
                self._description = self._device_info['host_name']
            elif self._device_info is not None and "ip" in self._device_info:
                self._name = f"{DOMAIN}_{self._data['ip']}"
                self._description = self._device_info['ip']
            else:
                self._name = f"{DOMAIN}_{self._mac_addr}"
                self._description = self._mac_addr

        else:
            self._port = identifier
            self._data_key = f"eth-{self._port}"
            self.unique_id = f"{DOMAIN}_eth_port_{self._port}"
            self._data = coordinator.ethernet_ports[f"{self._data_key}"]
            self.config_entry = config_entry
            self._description = f"Ethernet Port {self._port}"
            self._name = self.unique_id

        self._is_device = is_device

        # Override the entity_id so we can provide a better friendly name
        self.entity_id = f'device_tracker.{self._name}'

    @property
    def name(self):
        """Return the friendly name."""
        if self._description is not None:
            return self._description
        else:
            return self._name

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def is_connected(self):
        if self._is_device:
            return self._connected
        else:
            return "link" in self._data and self._data["link"] == True

    @property
    def icon(self):
        """Return the icon."""
        if self._is_device:
            return "mdi:lan-connect"
        else:
            return "mdi:ethernet"

    @property
    def mac_address(self):
        """Return the mac address of the device."""
        return self.unique_id

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self.coordinator.last_update_success and self._data is not None:
            return {**self._data, "last_seen": datetime.now().isoformat()}
        return {}

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        if self._is_device:
            if self.config_entry.data.get(CONF_ENABLE_NEW_DEVICES, False):
                return True
            else:
                return False
        else:
            return True

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
        if not self._is_device and self._data_key in self.coordinator.ethernet_ports:
            self._data = self.coordinator.ethernet_ports[self._data_key]
        elif self._is_device and self._data_key in self.coordinator.ethernet_devices:
            self._data = self.coordinator.ethernet_devices[self._data_key]

        _LOGGER.debug(
            f"entity={self.unique_id} was updated via _handle_coordinator_update"
        )
        super()._handle_coordinator_update()
