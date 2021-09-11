"""The Amplifi integration."""
import asyncio
import aiohttp
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.const import CONF_HOST, CONF_PASSWORD

from .const import DOMAIN, COORDINATOR, ENTITIES, COORDINATOR_LISTENER
from .coordinator import AmplifiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Amplifi integration is setup as a sensor integration
PLATFORMS = ["device_tracker", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Amplify component."""

    # Set the amplifi namespace
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amplify from a config entry."""

    # Create jar for storing session cookies
    jar = aiohttp.CookieJar(unsafe=True)

    # Amplifi uses session cookie so we need a we client with a cookie jar
    client_sesssion = async_create_clientsession(hass, False, True, cookie_jar=jar)

    coordinator = AmplifiDataUpdateCoordinator(
        hass, client_sesssion, entry.data[CONF_HOST], entry.data[CONF_PASSWORD]
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        ENTITIES: {},
        COORDINATOR_LISTENER: None,
    }

    # Setup the platforms for the amplifi integration
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    coordinator_listener = hass.data[DOMAIN][entry.entry_id][COORDINATOR_LISTENER]
    coordinator.async_remove_listener(coordinator_listener)

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
