"""Options-flow regressions against real Home Assistant, without runtime setup."""

import unittest
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResultType

# isort: split
# Home Assistant installs its validation compatibility aliases during import.
import voluptuous as vol

from custom_components.naver_weather_custom.config_flow import OptionsFlowHandler
from custom_components.naver_weather_custom.const import (
    CONF_AREA,
    CONF_BROWSER_URL,
    CONF_TODAY,
    DOMAIN,
)


def entry(data: dict[str, str | bool], options: dict[str, str | bool]) -> ConfigEntry:
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

    async def test_browser_address_is_suggested_without_becoming_a_default(self) -> None:
        address = "http://browser.invalid:8765"
        flow = OptionsFlowHandler(entry({CONF_AREA: "Synthetic"}, {CONF_BROWSER_URL: address}))
        result = await flow.async_step_init()
        schema = result.get("data_schema")
        assert schema is not None
        keys = list(schema.schema)
        self.assertEqual([key.schema for key in keys], [CONF_TODAY, CONF_BROWSER_URL])
        self.assertEqual(keys[1].description, {"suggested_value": address})
        self.assertEqual(schema({}), {CONF_TODAY: True})

    async def test_blank_browser_address_is_removed_from_saved_options(self) -> None:
        for address in ("", " \t\n "):
            with self.subTest(address=address):
                config_entry = entry({CONF_AREA: "Synthetic"}, {CONF_BROWSER_URL: "http://browser.invalid:8765"})
                flow = OptionsFlowHandler(config_entry)
                result = await flow.async_step_init({CONF_TODAY: False, CONF_BROWSER_URL: address})
                self.assertEqual(result.get("type"), FlowResultType.CREATE_ENTRY)
                self.assertEqual(result.get("data"), {CONF_TODAY: False})
                self.assertEqual(dict(config_entry.options), {CONF_BROWSER_URL: "http://browser.invalid:8765"})

    async def test_saving_keeps_options_the_form_does_not_show(self) -> None:
        config_entry = entry(
            {CONF_AREA: "Synthetic", CONF_TODAY: True},
            {CONF_AREA: "Legacy synthetic", CONF_BROWSER_URL: "http://old.example:8765"},
        )
        cases = [
            ({CONF_TODAY: False}, {CONF_AREA: "Legacy synthetic", CONF_TODAY: False}),
            (
                {CONF_TODAY: True, CONF_BROWSER_URL: "http://new.example:8765/"},
                {CONF_AREA: "Legacy synthetic", CONF_TODAY: True, CONF_BROWSER_URL: "http://new.example:8765"},
            ),
        ]
        for submitted, expected in cases:
            with self.subTest(submitted=submitted):
                result = await OptionsFlowHandler(config_entry).async_step_init(dict(submitted))
                self.assertEqual(result.get("type"), FlowResultType.CREATE_ENTRY)
                self.assertEqual(result.get("data"), expected)
        self.assertEqual(
            dict(config_entry.options),
            {CONF_AREA: "Legacy synthetic", CONF_BROWSER_URL: "http://old.example:8765"},
        )

    async def test_http_and_https_origins_are_trimmed_and_saved(self) -> None:
        for address, expected in (
            ("http://browser.invalid:8765", "http://browser.invalid:8765"),
            (" http://browser.invalid:8765/ ", "http://browser.invalid:8765"),
            ("https://browser.invalid/", "https://browser.invalid"),
            ("https://browser.invalid:443", "https://browser.invalid:443"),
            ("http://[::1]:8765/", "http://[::1]:8765"),
        ):
            with self.subTest(address=address):
                flow = OptionsFlowHandler(entry({CONF_AREA: "Synthetic"}, {}))
                result = await flow.async_step_init({CONF_TODAY: True, CONF_BROWSER_URL: address})
                self.assertEqual(result.get("type"), FlowResultType.CREATE_ENTRY)
                self.assertEqual(result.get("data"), {CONF_TODAY: True, CONF_BROWSER_URL: expected})

    async def test_invalid_browser_address_shows_field_error_without_saving(self) -> None:
        for address in (
            "ftp://browser.invalid", "browser.invalid:8765", "http:///missing",
            "http://user@browser.invalid", "http://user:pw@browser.invalid",
            "https://browser.invalid/render", "https://browser.invalid/?query=area",
            "https://browser.invalid/#fragment", "https://browser.invalid?",
            "https://browser.invalid#", "http://[bad", "http://browser.invalid:bad",
            "http://browser.invalid:99999", "http://bad host.invalid", "http://browser.\ninvalid",
        ):
            with self.subTest(address=address):
                config_entry = entry({CONF_AREA: "Synthetic"}, {})
                result = await OptionsFlowHandler(config_entry).async_step_init(
                    {CONF_TODAY: False, CONF_BROWSER_URL: address}
                )
                self.assertEqual(result.get("type"), FlowResultType.FORM)
                self.assertEqual(result.get("errors"), {CONF_BROWSER_URL: "invalid_browser_url"})
                self.assertNotIn("data", result)
                self.assertEqual(dict(config_entry.options), {})


if __name__ == "__main__":
    unittest.main()
