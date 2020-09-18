"""Support for Xiaomi Mi Smart toilet seat."""
import enum
import asyncio
import logging

import voluptuous as vol

from miio import Device, Toiletlid, DeviceException
from miio.toiletlid import ToiletlidStatus, AmbientLightColor
from homeassistant.const import STATE_UNAVAILABLE, STATE_IDLE
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_TOKEN, ATTR_ENTITY_ID
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Toiletlid"
DATA_KEY = "toiletlid.xiaomi_miio"

DOMAIN = "toiletlid"
CONF_MODEL = "model"
MODEL_TOILETLID_V1 = "tinymu.toiletlid.v1"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MODEL): vol.In([MODEL_TOILETLID_V1]),
    }
)

ATTR_MODEL = "model"

ATTR_WORK_STATE = "work_state"
ATTR_WORK_MODE = "work_mode"
ATTR_AMBIENT_LIGHT = "ambient_light"
ATTR_FILTER_USE_PERCENTAGE = "filter_use_percentage"
ATTR_FILTER_REMAINING_TIME = "filter_remaining_time"

SERVICE_SET_AMBIENT_LIGHT = "set_ambient_light"
SERVICE_NOZZLE_CLEAN = "nozzle_clean"

AVAILABLE_ATTRIBUTES_TOILETLID = [
    ATTR_WORK_STATE,
    ATTR_WORK_MODE,
    ATTR_AMBIENT_LIGHT,
    ATTR_FILTER_USE_PERCENTAGE,
    ATTR_FILTER_REMAINING_TIME,
]

SUCCESS = ["ok"]

TOILETLID_SERVICE_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})

SERVICE_SCHEMA_AMBIENT_LIGHT = TOILETLID_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_AMBIENT_LIGHT): vol.All(
            vol.Coerce(int), vol.Clamp(min=0, max=7)
        )
    }
)

SERVICE_TO_METHOD = {
    SERVICE_SET_AMBIENT_LIGHT: {
        "method": "set_ambient_light",
        "schema": SERVICE_SCHEMA_AMBIENT_LIGHT,
    },
    SERVICE_NOZZLE_CLEAN: {"method": "nozzle_clean"},
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the miio toiletlid device from config."""

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    model = config.get(CONF_MODEL)

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])
    try:
        miio_device = Device(host, token)
        device_info = miio_device.info()
        model = device_info.model or model or MODEL_TOILETLID_V1
        unique_id = "{}-{}".format(model, device_info.mac_address)
    except DeviceException:
        raise PlatformNotReady
    toiletlid = Toiletlid(host, token, model=model)
    device = XiaomiToiletlid(name, toiletlid, model, unique_id)
    hass.data[DATA_KEY][host] = device
    async_add_entities([device], update_before_add=True)

    async def async_service_handler(service):
        """Map services to methods on XiaomiToiletlid."""
        method = SERVICE_TO_METHOD.get(service.service)
        params = service.data.copy()
        entity_ids = params.pop(ATTR_ENTITY_ID, hass.data[DATA_KEY].values())
        update_tasks = []
        for device in filter(
                lambda x: x.entity_id in entity_ids, hass.data[DATA_KEY].values()
        ):
            if not hasattr(device, method["method"]):
                continue
            await getattr(device, method["method"])(**params)
            update_tasks.append(device.async_update_ha_state(True))

        if update_tasks:
            await asyncio.wait(update_tasks)

    for toiletlid_service in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[toiletlid_service].get(
            "schema", TOILETLID_SERVICE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, toiletlid_service, async_service_handler, schema=schema
        )


class XiaomiToiletlid(Entity):
    def __init__(self, name, device, model, unique_id):
        """Initialize the generic Xiaomi device."""
        self._name = name
        self._device: Toiletlid = device
        self._model = model
        self._unique_id = unique_id

        self._state = None
        self._available = False
        self._state_attrs = {ATTR_MODEL: self._model}
        self._state_attrs.update(
            {attribute: None for attribute in AVAILABLE_ATTRIBUTES_TOILETLID}
        )

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the device if any."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def state(self) -> str:
        """Return the state."""
        return STATE_UNAVAILABLE if self.is_on else STATE_IDLE

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return "mdi:toilet"

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._state

    from homeassistant.components import yeelight

    async def async_update(self):
        """Fetch state from the device."""
        try:
            state: ToiletlidStatus = await self.hass.async_add_executor_job(
                self._device.status
            )
            _LOGGER.debug("Got new state: %s", state)
            self._available = True
            for key in AVAILABLE_ATTRIBUTES_TOILETLID:
                value = getattr(state, key)
                if isinstance(value, enum.Enum):
                    value = value.name
                self._state_attrs.update({key: value})
            self._state = state.is_on

        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    async def nozzle_clean(self) -> bool:
        """Nozzle clean."""
        try:
            return (
                    await self.hass.async_add_executor_job(self._device.nozzle_clean)
                    == SUCCESS
            )
        except DeviceException as exc:
            _LOGGER.error("Call nozzle clean failure: %s", exc)
            self._available = False
            return False

    async def set_ambient_light(self, ambient_light: int = 0) -> bool:
        """Set ambient light."""
        color = AmbientLightColor(str(ambient_light))
        try:
            return (
                    await self.hass.async_add_executor_job(
                        lambda: self._device.set_ambient_light(color)
                    )
                    == SUCCESS
            )
        except DeviceException as exc:
            _LOGGER.error("Set ambient light failure: %s", exc)
            self._available = False
            return False
