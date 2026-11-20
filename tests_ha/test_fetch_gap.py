"""Exercise the shared location refresh lock and gap with a controllable clock."""

import asyncio
import logging
from types import SimpleNamespace

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.naver_weather_custom import coordinator as coordinator_module
from custom_components.naver_weather_custom.api_nweather import NWeatherAPI
from custom_components.naver_weather_custom.const import CONF_AREA, DOMAIN
from custom_components.naver_weather_custom.coordinator import (
    NWeatherDataUpdateCoordinator,
)

FETCH_GAP = 30.0


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.waits: list[float] = []

    async def sleep(self, delay: float) -> None:
        self.waits.append(delay)
        self.now += delay


@pytest.fixture
def clock(no_fetch_gap, monkeypatch):
    """Restore the production gap and replace only the coordinator's clock and sleep."""
    clock = Clock()
    monkeypatch.setattr(coordinator_module, "FETCH_GAP", FETCH_GAP)
    monkeypatch.setattr(coordinator_module, "monotonic", lambda: clock.now)
    monkeypatch.setattr(coordinator_module, "asyncio", SimpleNamespace(sleep=clock.sleep))
    return clock


def _entry(hass, area):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: area}, unique_id=area)
    entry.add_to_hass(hass)
    return entry


def _coordinator(hass, area):
    entry = _entry(hass, area)
    return NWeatherDataUpdateCoordinator(hass, NWeatherAPI(hass, entry, 1), entry)


async def test_first_refreshes_are_serial_and_later_refreshes_wait(hass, clock, monkeypatch):
    first = _coordinator(hass, "검증동")
    second = _coordinator(hass, "검증2동")
    started, release = asyncio.Event(), asyncio.Event()
    starts = []

    async def update(api):
        starts.append((api, clock.now))
        if len(starts) == 1:
            started.set()
            await asyncio.wait_for(release.wait(), 2)
        clock.now += 3
        api.result = {}

    monkeypatch.setattr(NWeatherAPI, "update", update)
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(first._async_update_data())
        await asyncio.wait_for(started.wait(), 2)
        tasks.create_task(second._async_update_data())
        await asyncio.sleep(0)
        assert starts == [(first.api, 100.0)] and clock.waits == []
        release.set()
    assert starts == [(first.api, 100.0), (second.api, 103.0)] and clock.waits == []

    await first._async_update_data()
    assert starts[-1] == (first.api, 106.0 + FETCH_GAP)
    assert clock.waits == [FETCH_GAP]


async def test_gap_sleep_leaves_lock_free_and_rechecks_after_other_fetch(hass, clock, monkeypatch):
    first = _coordinator(hass, "검증동")
    second = _coordinator(hass, "검증2동")
    sleeping, other_ended = asyncio.Event(), asyncio.Event()
    starts = []

    async def sleep(delay):
        wake = clock.now + delay
        clock.waits.append(delay)
        sleeping.set()
        await asyncio.wait_for(other_ended.wait(), 2)
        clock.now = max(wake, clock.now)

    async def update(api):
        starts.append((api, clock.now))
        clock.now += 5
        api.result = {}

    monkeypatch.setattr(coordinator_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(NWeatherAPI, "update", update)
    await first._async_update_data()
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(first._async_update_data())
        await asyncio.wait_for(sleeping.wait(), 2)
        await asyncio.wait_for(second._async_update_data(), 2)
        assert starts == [(first.api, 100.0), (second.api, 105.0)]
        other_ended.set()

    assert clock.waits == [FETCH_GAP, 5.0]
    assert starts[-1] == (first.api, 110.0 + FETCH_GAP)


async def test_failed_update_releases_lock_and_sets_gap_start(hass, clock, monkeypatch):
    first = _coordinator(hass, "검증동")
    second = _coordinator(hass, "검증2동")
    starts = []

    async def update(api):
        starts.append(clock.now)
        clock.now += 4
        if api is second.api:
            raise RuntimeError("synthetic refresh failure")
        api.result = {}

    monkeypatch.setattr(NWeatherAPI, "update", update)
    await first._async_update_data()
    with pytest.raises(RuntimeError, match="synthetic refresh failure"):
        await asyncio.wait_for(second._async_update_data(), 2)
    await asyncio.wait_for(first._async_update_data(), 2)
    assert starts == [100.0, 104.0, 108.0 + FETCH_GAP]
    assert clock.waits == [FETCH_GAP]


async def test_queued_refresh_does_not_fetch_after_entry_unload(hass, clock, monkeypatch, caplog):
    first = _entry(hass, "검증동")
    second = _entry(hass, "검증2동")
    started, release = asyncio.Event(), asyncio.Event()
    starts = []
    block = False

    async def update(api):
        starts.append(api.entry.entry_id)
        if block and api.entry.entry_id == first.entry_id:
            started.set()
            await asyncio.wait_for(release.wait(), 2)
        api.result = {"NowTemp": "21.5"}

    monkeypatch.setattr(NWeatherAPI, "update", update)
    # Setting up the domain's first entry sets up every entry of the domain.
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is second.state is ConfigEntryState.LOADED
    coordinators = hass.data[DOMAIN]["coordinators"]
    running, waiting = coordinators[first.entry_id], coordinators[second.entry_id]
    previous = waiting.data
    block = True
    clock.now += FETCH_GAP
    starts.clear()
    caplog.clear()

    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(running._async_update_data())
        await asyncio.wait_for(started.wait(), 2)
        queued = tasks.create_task(waiting._async_update_data())
        await asyncio.sleep(0)
        assert starts == [first.entry_id] and not queued.done()
        assert await hass.config_entries.async_unload(second.entry_id)
        release.set()
    assert queued.result() is previous
    assert starts == [first.entry_id]
    assert not any(
        record.levelno > logging.DEBUG and record.name.startswith("custom_components.naver_weather_custom")
        for record in caplog.records
    )
