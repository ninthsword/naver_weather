"""Options-flow regressions against real Home Assistant, without runtime setup."""

import unittest
from types import MappingProxyType

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResultType

from custom_components.naver_weather_custom.config_flow import OptionsFlowHandler
from custom_components.naver_weather_custom.const import CONF_AREA, CONF_TODAY, DOMAIN


def entry(data: dict[str, str | bool], options: dict[str, bool]) -> ConfigEntry:
    """Build a synthetic entry without a running Home Assistant instance."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Synthetic weather",
        data=data,
        options=options,
        source="user",
        unique_id="synthetic-weather",
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )


class OptionsFlowTest(unittest.IsolatedAsyncioTestCase):
    """Exercise the getter-only HA base separately from lightweight module shims."""

    async def test_constructor_and_options_data_default_precedence(self) -> None:
        descriptor = OptionsFlow.__dict__["config_entry"]
        self.assertIsInstance(descriptor, property)
        self.assertIsNone(descriptor.fset)
        cases = [
            ({CONF_AREA: "Synthetic", CONF_TODAY: True}, {CONF_TODAY: False}, False),
            ({CONF_AREA: "Synthetic", CONF_TODAY: False}, {CONF_TODAY: True}, True),
            ({CONF_AREA: "Synthetic", CONF_TODAY: False}, {}, False),
            ({CONF_AREA: "Synthetic", CONF_TODAY: True}, {}, True),
            ({CONF_AREA: "Synthetic"}, {}, True),
        ]
        for data, options, expected in cases:
            with self.subTest(data=data, options=options):
                flow = OptionsFlowHandler(entry(data, options))
                result = await flow.async_step_init()
                self.assertEqual(result.get("type"), FlowResultType.FORM)
                schema = result.get("data_schema")
                assert schema is not None
                self.assertEqual(schema({}), {CONF_TODAY: expected})
                with self.assertRaises(vol.Invalid):
                    schema({CONF_AREA: "Another synthetic area"})

    async def test_submitted_today_is_preserved_without_mutating_entry(self) -> None:
        config_entry = entry({CONF_AREA: "Synthetic", CONF_TODAY: True}, {})
        flow = OptionsFlowHandler(config_entry)
        result = await flow.async_step_init({CONF_TODAY: False})
        self.assertEqual(result.get("type"), FlowResultType.CREATE_ENTRY)
        self.assertEqual(result.get("data"), {CONF_TODAY: False})
        self.assertEqual(dict(config_entry.data), {CONF_AREA: "Synthetic", CONF_TODAY: True})
        self.assertEqual(dict(config_entry.options), {})


if __name__ == "__main__":
    unittest.main()
