"""The Amplifi integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_HOST, CONF_PASSWORD

from .const import DOMAIN, COORDINATOR, ENTITIES
from .coordinator import AmplifiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Amplifi integration is setup as a sensor integration
PLATFORMS = ["sensor", "device_tracker"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Amplify component."""

    # Set the amplifi namespace
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amplify from a config entry."""

    coordinator = AmplifiDataUpdateCoordinator(
        hass, entry.data[CONF_HOST], entry.data[CONF_PASSWORD]
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {COORDINATOR: coordinator, ENTITIES: {}}

    # Setup the platforms for the amplifi integration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def async_stop_coordinator():
        coordinator._async_stop_refresh(None)

    entry.async_on_unload(async_stop_coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
