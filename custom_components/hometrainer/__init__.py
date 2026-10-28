"""Intégration HomeTrainer To Home Assistant : un home trainer envoie ses mesures par webhook."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_CLOUDHOOK_URL, CONF_WEBHOOK_ID, DOMAIN
from .trainer import Settings, Trainer

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.TEXT,
]

type HomeTrainerConfigEntry = ConfigEntry[Trainer]

_NUMBER = vol.Any(None, vol.Coerce(float))
PAYLOAD_SCHEMA = vol.Schema(
    {
        vol.Optional("power"): _NUMBER,
        vol.Optional("cadence"): _NUMBER,
        vol.Optional("speed"): _NUMBER,
        vol.Optional("heart_rate"): _NUMBER,
        vol.Optional("distance"): _NUMBER,
        vol.Optional("energy"): _NUMBER,
        vol.Optional("device"): vol.Any(None, cv.string),
        vol.Optional("test", default=False): cv.boolean,
    },
    extra=vol.REMOVE_EXTRA,
)


async def async_setup_entry(hass: HomeAssistant, entry: HomeTrainerConfigEntry) -> bool:
    """Crée le home trainer, ses entités et son webhook."""

    @callback
    def save_settings(settings: Settings) -> None:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, **settings.as_options()}
        )

    trainer = Trainer(
        Settings.from_options(entry.options),
        now=dt_util.utcnow,
        on_settings_changed=save_settings,
    )
    entry.runtime_data = trainer

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        try:
            raw: Any = await request.json()
        except ValueError:
            return web.json_response({"ok": False, "error": "JSON invalide"}, status=400)
        try:
            data = PAYLOAD_SCHEMA(raw)
        except vol.Invalid as err:
            return web.json_response({"ok": False, "error": str(err)}, status=400)
        if not data["test"]:
            trainer.handle_data(data)
        return web.json_response(
            {
                "ok": True,
                "name": entry.title,
                "on_bike": trainer.on_bike,
                "zone": trainer.zone,
                "ftp": trainer.settings.ftp,
            }
        )

    webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        entry.data[CONF_WEBHOOK_ID],
        handle_webhook,
        local_only=False,
        allowed_methods=["POST"],
    )
    entry.async_on_unload(
        lambda: webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    )
    @callback
    def tick(_now: datetime) -> None:
        trainer.tick()

    entry.async_on_unload(async_track_time_interval(hass, tick, timedelta(seconds=1)))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: HomeTrainerConfigEntry
) -> None:
    """Options changées (bouton « Configurer » ou entités de réglage) : pas de rechargement."""
    trainer = entry.runtime_data
    new = Settings.from_options(entry.options)
    if new != trainer.settings:
        trainer.settings = new
        trainer.tick()


async def async_unload_entry(hass: HomeAssistant, entry: HomeTrainerConfigEntry) -> bool:
    """Décharge l'entrée."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Supprime l'adresse Nabu Casa éventuellement créée."""
    if entry.data.get(CONF_CLOUDHOOK_URL) and "cloud" in hass.config.components:
        from homeassistant.components import cloud  # noqa: PLC0415

        try:
            await cloud.async_delete_cloudhook(hass, entry.data[CONF_WEBHOOK_ID])
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Impossible de supprimer le cloudhook", exc_info=True)

