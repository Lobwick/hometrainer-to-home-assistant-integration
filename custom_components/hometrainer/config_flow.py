"""Configuration de HomeTrainer To Home Assistant depuis l'interface."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLOUDHOOK_URL,
    CONF_WEBHOOK_ID,
    DEFAULT_FTP,
    DEFAULT_NAME,
    DEFAULT_OPTIONS,
    DOMAIN,
    OPT_FTP,
    OPT_STALE_TIMEOUT,
    OPT_ZONE_THRESHOLDS,
)
from .urls import webhook_urls

_LOGGER = logging.getLogger(__name__)

ZONE_LABELS = ("zone_2", "zone_3", "zone_4", "zone_5", "zone_6")


def _percent_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=300, step=1, unit_of_measurement="%",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


class HomeTrainerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ajout d'un home trainer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Nom de l'appareil et FTP."""
        if user_input is not None:
            webhook_id = webhook.async_generate_id()
            data = {CONF_NAME: user_input[CONF_NAME], CONF_WEBHOOK_ID: webhook_id}
            if "cloud" in self.hass.config.components:
                from homeassistant.components import cloud  # noqa: PLC0415

                if cloud.async_active_subscription(self.hass):
                    try:
                        data[CONF_CLOUDHOOK_URL] = await cloud.async_create_cloudhook(
                            self.hass, webhook_id
                        )
                    except Exception:  # noqa: BLE001
                        _LOGGER.warning("Création de l'adresse Nabu Casa impossible")
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=data,
                options={**DEFAULT_OPTIONS, OPT_FTP: int(user_input[OPT_FTP])},
                description_placeholders=webhook_urls(
                    self.hass, webhook_id, data.get(CONF_CLOUDHOOK_URL)
                ),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(OPT_FTP, default=DEFAULT_FTP): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=50, max=600, step=1, unit_of_measurement="W",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Bouton « Configurer »."""
        return HomeTrainerOptionsFlow()


class HomeTrainerOptionsFlow(OptionsFlow):
    """Adresse du webhook et réglages avancés (seuils des zones, délai de déconnexion).

    La FTP, le délai « sur le vélo » et les couleurs se règlent directement
    depuis les entités de configuration de l'appareil.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Affiche l'adresse du webhook et les réglages avancés."""
        options = {**DEFAULT_OPTIONS, **self.config_entry.options}
        thresholds = list(options[OPT_ZONE_THRESHOLDS])
        errors: dict[str, str] = {}

        if user_input is not None:
            new = [float(user_input[label]) for label in ZONE_LABELS]
            if new != sorted(new) or len(set(new)) != len(new):
                errors["base"] = "thresholds_order"
            else:
                return self.async_create_entry(
                    data={
                        **options,
                        OPT_ZONE_THRESHOLDS: new,
                        OPT_STALE_TIMEOUT: int(user_input[OPT_STALE_TIMEOUT]),
                    }
                )
            thresholds = new

        schema = {
            vol.Required(label, default=thresholds[i]): _percent_selector()
            for i, label in enumerate(ZONE_LABELS)
        }
        schema[vol.Required(OPT_STALE_TIMEOUT, default=options[OPT_STALE_TIMEOUT])] = (
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=2, max=60, step=1, unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            )
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders=webhook_urls(
                self.hass,
                self.config_entry.data[CONF_WEBHOOK_ID],
                self.config_entry.data.get(CONF_CLOUDHOOK_URL),
            ),
        )
