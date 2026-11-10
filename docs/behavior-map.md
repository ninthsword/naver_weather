# Behavior map: Naver weather refresh and parsing

Scope: core-flow navigation for the existing implementation, not a new feature or runtime policy.
Start from the relevant row; keep architecture and safety intent in `AGENTS.md`, durable decisions
in the existing decision record, and dated acceptance/deployment in the current work record.

- **SOURCE**: `master` at `c54675f79bf36762c2ea0b11fdb6890069775e8c` (release 2.5.3-0.5), refreshed on 2026-11-11.
- **TEST LINK**: relevant executable checks to consult; this documentation task did not rerun product tests.
- **RECORDED**: dated project acceptance/deployment evidence, separate from these source links.
- **UNKNOWN**: live behavior not measured by this map. Hash equality does not establish semantic correctness.

| Scenario | Input, decision and effect | Evidence navigation |
|---|---|---|
| Shared refresh | A single coordinator awaits the API update and exposes its result to all platforms. Weather and air request failure remains an all-or-nothing refresh failure; platforms do not poll independently. Entities keep the last good payload for up to one hour of failed refreshes, then become unavailable; the coordinator notifies them itself because Home Assistant notifies only on the first of consecutive failures. | **SOURCE**: [coordinator.py](../custom_components/naver_weather_custom/coordinator.py), [api_nweather.py](../custom_components/naver_weather_custom/api_nweather.py); **TEST LINK**: [test_integration_contract.py](../tests/test_integration_contract.py), [test_setup_lifecycle.py](../tests_ha/test_setup_lifecycle.py) |
| Markup, time and missing fields | The API parser resolves daily/hourly KST timestamps and publication times, and retains previous humidity through its explicit fallback. The air request follows the weather page's local air-quality link only when it is https on Naver search, otherwise the area query. Use the compatibility helper for markup-library differences. | **SOURCE**: [api_nweather.py](../custom_components/naver_weather_custom/api_nweather.py), [bs4_compat.py](../custom_components/naver_weather_custom/bs4_compat.py); **TEST LINK**: [test_integration_contract.py](../tests/test_integration_contract.py), [test_parser_dependency.py](../tests_ha/test_parser_dependency.py) |
| Setup and unload | Setup establishes the coordinator and first refresh before platform forwarding. Review first-refresh and unload failure paths together with refresh behavior. | **SOURCE**: [__init__.py](../custom_components/naver_weather_custom/__init__.py); **TEST LINK**: [test_integration_contract.py](../tests/test_integration_contract.py), [test_setup_lifecycle.py](../tests_ha/test_setup_lifecycle.py) |

## Boundaries and unknowns

Contract tests establish the intended refresh/lifecycle boundary, not comprehensive coverage of every markup variation. Current upstream markup, network availability and live forecast accuracy are UNKNOWN.

## Freshness and reconsideration

Revisit the affected row when changing refresh ownership, partial-result policy, markup selectors, timestamp resolution or lifecycle failure handling.
Review linked tests and the existing decision rationale before changing those boundaries.
Keep proposals in a task plan until accepted; distinguish local source from publication and deployment.

The optional local harness command `python3 -B ~/.local/share/harness-context/check_context.py`
compares registered source/test/map hashes. A change requests review, not automatic re-baselining.
It is not a portable project dependency, CI gate or proof that the complete project is mapped.
