"""Platform for sensor integration."""
from homeassistant.components.sensor import SensorEntity
import logging

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from homeassistant.const import DATA_RATE_MEGABITS_PER_SECOND

from .const import DOMAIN, COORDINATOR, COORDINATOR_LISTENER, ENTITIES

_LOGGER = logging.getLogger(__name__)
WAN_SPEED_SENSOR_TYPES = ["download", "upload"]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    """Add internet speed sensors."""
    for speed_sensor_type in WAN_SPEED_SENSOR_TYPES:
        wan_sensor_unique_id = f"{DOMAIN}_wan_{speed_sensor_type}_speed"
        if (
            wan_sensor_unique_id
            not in hass.data[DOMAIN][config_entry.entry_id][ENTITIES]
        ):
            async_add_entities(
                [
                    AmplifiWanSpeedSensor(
                        coordinator, config_entry, speed_sensor_type
                    )
                ]
            )

class AmplifiWanSpeedSensor(CoordinatorEntity, SensorEntity):
    """Sensor class representing a internet speed of amplifi."""

    name = None
    unique_id = None

    def __init__(self, coordinator, config_entry, speed_sensor_type):
        """Initialize amplifi sensor."""
        self.unique_id = f"{DOMAIN}_wan_{speed_sensor_type}_speed"
        self.name = self.unique_id
        self.config_entry = config_entry
        self._speed_sensor_type = speed_sensor_type
        self._value = 0
        super().__init__(coordinator)

    @property
    def available(self):
        """Return if sensor is available."""
        return True

    @property
    def state(self):
        """State of the sensor."""
        return round(self._value, 3)

    @property
    def icon(self):
        """Return the icon."""
        return f"mdi:{self._speed_sensor_type}-network"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return DATA_RATE_MEGABITS_PER_SECOND

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
        self._value = self.coordinator.wan_speeds[self._speed_sensor_type]
        super()._handle_coordinator_update()
