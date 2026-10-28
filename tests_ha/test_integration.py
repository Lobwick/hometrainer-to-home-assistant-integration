"""Tests de bout en bout dans un vrai Home Assistant de test."""

from datetime import timedelta

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.hometrainer.const import DOMAIN

PREFIX = "home_trainer"


async def _setup(hass: HomeAssistant):
    await async_setup_component(hass, "http", {})
    await async_setup_component(hass, "webhook", {})
    hass.config.internal_url = "http://192.168.1.33:8123"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Home trainer", "ftp": 252}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "/api/webhook/" in result["description_placeholders"]["local_url"]
    await hass.async_block_till_done()
    return hass.config_entries.async_entries(DOMAIN)[0]


async def test_full_flow(hass: HomeAssistant, hass_client_no_auth, freezer) -> None:
    entry = await _setup(hass)
    client = await hass_client_no_auth()
    url = f"/api/webhook/{entry.data['webhook_id']}"

    # entités présentes avant toute donnée
    assert hass.states.get(f"sensor.{PREFIX}_power").state == "0"
    assert hass.states.get(f"binary_sensor.{PREFIX}_on_bike").state == "off"
    assert hass.states.get(f"number.{PREFIX}_ftp").state == "252"
    assert hass.states.get(f"text.{PREFIX}_zone_1_colour").state == "#A0A0A0"

    # test de connexion depuis l'app
    resp = await client.post(url, json={"test": True})
    assert resp.status == 200
    assert (await resp.json())["ok"] is True
    assert hass.states.get(f"binary_sensor.{PREFIX}_app_connected").state == "off"

    # pédalage minimum par défaut : 5 min, un seul envoi ne suffit pas
    assert hass.states.get(f"number.{PREFIX}_minimum_pedaling").state == "5"
    await hass.services.async_call("number", "set_value", {"entity_id": f"number.{PREFIX}_minimum_pedaling", "value": 0}, blocking=True)
    resp = await client.post(url, json={"power": 260, "cadence": 92, "speed": 36.4, "heart_rate": 151, "device": "KICKR CORE"})
    assert resp.status == 200
    body = await resp.json()
    assert body["zone"] == 4 and body["on_bike"] is True
    await hass.async_block_till_done()

    assert hass.states.get(f"sensor.{PREFIX}_power").state == "260.0"
    assert hass.states.get(f"sensor.{PREFIX}_cadence").state == "92.0"
    zone = hass.states.get(f"sensor.{PREFIX}_power_zone")
    assert zone.state == "4"
    assert zone.attributes["rgb_color"] == [255, 215, 0]
    assert hass.states.get(f"binary_sensor.{PREFIX}_on_bike").state == "on"
    connected = hass.states.get(f"binary_sensor.{PREFIX}_app_connected")
    assert connected.state == "on" and connected.attributes["trainer"] == "KICKR CORE"

    # changement de FTP depuis l'entité : zone recalculée et option enregistrée
    await hass.services.async_call("number", "set_value", {"entity_id": f"number.{PREFIX}_ftp", "value": 220}, blocking=True)
    assert hass.states.get(f"sensor.{PREFIX}_power_zone").state == "5"
    assert entry.options["ftp"] == 220

    # couleur invalide refusée, valide acceptée
    import pytest
    from homeassistant.exceptions import ServiceValidationError
    with pytest.raises((ValueError, ServiceValidationError)):
        await hass.services.async_call("text", "set_value", {"entity_id": f"text.{PREFIX}_zone_5_colour", "value": "rouge"}, blocking=True)
    await hass.services.async_call("text", "set_value", {"entity_id": f"text.{PREFIX}_zone_5_colour", "value": "#123456"}, blocking=True)
    assert hass.states.get(f"sensor.{PREFIX}_power_zone").attributes["hex_color"] == "#123456"
    assert entry.options["zone_colors"][4] == "#123456"

    # l'app s'arrête : puissance à 0 après 5 s, toujours sur le vélo
    freezer.tick(timedelta(seconds=7))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{PREFIX}_power").state == "0"
    assert hass.states.get(f"sensor.{PREFIX}_power_zone").state == "0"
    assert hass.states.get(f"binary_sensor.{PREFIX}_app_connected").state == "off"
    assert hass.states.get(f"binary_sensor.{PREFIX}_on_bike").state == "on"

    # délai réglé à 1 min : plus sur le vélo ensuite
    await hass.services.async_call("number", "set_value", {"entity_id": f"number.{PREFIX}_on_bike_delay", "value": 1}, blocking=True)
    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(f"binary_sensor.{PREFIX}_on_bike").state == "off"

    # JSON invalide
    resp = await client.post(url, data="pas du json")
    assert resp.status == 400

    # options : seuils non croissants refusés
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone_2": 76, "zone_3": 60, "zone_4": 90, "zone_5": 105, "zone_6": 119, "stale_timeout": 5}
    )
    assert result["errors"] == {"base": "thresholds_order"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone_2": 55, "zone_3": 75, "zone_4": 90, "zone_5": 105, "zone_6": 120, "stale_timeout": 10}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.settings.zone_thresholds == [55, 75, 90, 105, 120]
    assert entry.runtime_data.settings.ftp == 220  # réglages conservés

    # déchargement propre
    assert await hass.config_entries.async_unload(entry.entry_id)
    resp = await client.post(url, json={"power": 100})
    assert resp.status == 200  # webhook inconnu : HA répond 200 sans rien faire
