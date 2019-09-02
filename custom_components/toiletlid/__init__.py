"""Component to Toilet seat."""
import logging
from datetime import timedelta

from homeassistant.components import group
from homeassistant.loader import bind_hass
from homeassistant.helpers.entity_component import EntityComponent

_LOGGER = logging.getLogger(__name__)
DOMAIN = "toiletlid"

SCAN_INTERVAL = timedelta(seconds=30)

GROUP_NAME_ALL_TOILETLID = "all toiletlid"
ENTITY_ID_ALL_TOILETLID = group.ENTITY_ID_FORMAT.format(GROUP_NAME_ALL_TOILETLID)
ENTITY_ID_FORMAT = DOMAIN + ".{}"


@bind_hass
def is_on(hass, entity_id: str = None) -> bool:
    if hass.states.get(entity_id):
        return True
    else:
        return False


async def async_setup(hass, config):
    """Set up the Toiletlid component."""
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL, ENTITY_ID_ALL_TOILETLID
    )
    await component.async_setup(config)
    return True


async def async_setup_entry(hass, entry):
    """Set up a config entry."""
    return await hass.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry)
