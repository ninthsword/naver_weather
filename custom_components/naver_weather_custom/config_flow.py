"""Config flow for naver_weather."""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback

from .const import CONF_AREA, CONF_TODAY, DEFAULT_AREA, DOMAIN


def canonical_area(area: str | None) -> str:
    """Return a stable comparison key without changing stored area text."""
    normalized = " ".join((area or "").split()).casefold()
    return normalized or DEFAULT_AREA.casefold()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Naver Weather."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str | bool] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            area = user_input.get(CONF_AREA, DEFAULT_AREA)
            if area and not isinstance(area, str):
                raise TypeError("Area must be text")
            if not area or not area.strip():
                area = DEFAULT_AREA
            user_input[CONF_AREA] = area
            normalized_area = canonical_area(area)
            await self.async_set_unique_id(normalized_area)
            if self._area_is_configured(normalized_area):
                return self.async_abort(reason="already_configured")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=area, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_AREA): cv.string,
                    vol.Optional(CONF_TODAY, default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, str | bool] | None = None) -> ConfigFlowResult:
        """Handle configuration by yaml file."""
        if user_input is None:
            raise TypeError("Import data is required")
        area = user_input[CONF_AREA]
        if area and not isinstance(area, str):
            raise TypeError("Area must be text")
        if not area or not area.strip():
            area = DEFAULT_AREA
            user_input[CONF_AREA] = area
        normalized_area = canonical_area(area)
        await self.async_set_unique_id(normalized_area)
        if self._area_is_configured(normalized_area):
            return self.async_abort(reason="already_configured")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=area, data=user_input)

    def _area_is_configured(self, normalized_area: str) -> bool:
        """Return whether a canonical area matches a new or legacy entry."""
        for entry in self._async_current_entries():
            entry_area = entry.options.get(
                CONF_AREA, entry.data.get(CONF_AREA, DEFAULT_AREA)
            )
            if canonical_area(entry_area) == normalized_area:
                return True
        return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "OptionsFlowHandler":
        """Expose only the existing forecast display preference after setup."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Keep the existing ``today`` option without allowing area changes."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize the options flow."""
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, bool] | None = None) -> ConfigFlowResult:
        """Edit only the existing today preference."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        today = self._entry.options.get(
            CONF_TODAY, self._entry.data.get(CONF_TODAY, True)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Optional(CONF_TODAY, default=today): bool}),
        )
