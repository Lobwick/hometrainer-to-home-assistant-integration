"""Adresses du webhook à saisir dans l'app."""

from __future__ import annotations

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError, get_url


def webhook_urls(
    hass: HomeAssistant, webhook_id: str, cloudhook_url: str | None = None
) -> dict[str, str]:
    """Adresse sur le réseau local et adresse depuis Internet (Nabu Casa ou URL externe)."""
    path = webhook.async_generate_path(webhook_id)
    urls = {"local_url": "—", "external_url": "—"}
    try:
        urls["local_url"] = get_url(hass, allow_external=False) + path
    except NoURLAvailableError:
        pass
    if cloudhook_url:
        urls["external_url"] = cloudhook_url
    else:
        try:
            urls["external_url"] = (
                get_url(hass, allow_internal=False, allow_cloud=False) + path
            )
        except NoURLAvailableError:
            pass
    return urls
