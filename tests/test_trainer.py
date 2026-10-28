"""Tests de la logique : zones, puissance lissée, « sur le vélo », déconnexion."""

from datetime import datetime, timedelta, timezone

from ht_core.trainer import Settings, Trainer, hex_to_rgb


class Clock:
    def __init__(self) -> None:
        self.t = datetime(2026, 10, 28, 18, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t += timedelta(**kw)


def make(**settings):
    clock = Clock()
    saved = []
    trainer = Trainer(Settings(**settings), now=clock, on_settings_changed=saved.append)
    return trainer, clock, saved


def test_initial_state():
    t, _, _ = make()
    assert not t.connected
    assert not t.on_bike
    assert t.metric("power") == 0
    assert t.metric("heart_rate") is None
    assert t.zone == 0


def test_zones_follow_ftp():
    t, clock, _ = make(ftp=252)
    expected = {100: 1, 160: 2, 200: 3, 240: 4, 280: 5, 320: 6}
    for watts, zone in expected.items():
        clock.advance(seconds=10)  # vide la fenêtre de lissage
        t.handle_data({"power": watts})
        assert t.zone == zone, watts
    # 60 % de 252 = 151,2 W : 151 W est encore en zone 1
    clock.advance(seconds=10)
    t.handle_data({"power": 151})
    assert t.zone == 1


def test_zone_attributes():
    t, clock, _ = make(ftp=200)
    t.handle_data({"power": 200})
    attrs = t.zone_attributes()
    assert t.zone == 4
    assert attrs["zone_name"] == "Seuil"
    assert attrs["hex_color"] == "#FFD700"
    assert attrs["rgb_color"] == [255, 215, 0]
    assert attrs["power_min"] == 180 and attrs["power_max"] == 210


def test_power_average_window():
    t, clock, _ = make()
    t.handle_data({"power": 100})
    clock.advance(seconds=1)
    t.handle_data({"power": 200})
    clock.advance(seconds=1)
    t.handle_data({"power": 300})
    assert t.power_avg == 200
    clock.advance(seconds=3)
    t.handle_data({"power": 300})
    assert t.power_avg == 300


def test_disconnect_zeroes_power_but_keeps_on_bike():
    t, clock, _ = make(on_bike_delay=20, stale_timeout=5)
    t.handle_data({"power": 250, "cadence": 90, "speed": 35.2, "heart_rate": 150, "distance": 1200})
    assert t.on_bike and t.connected
    clock.advance(seconds=6)
    t.tick()
    assert not t.connected
    assert t.metric("power") == 0 and t.metric("cadence") == 0 and t.metric("speed") == 0
    assert t.metric("heart_rate") is None
    assert t.metric("distance") == 1200
    assert t.zone == 0
    assert t.on_bike  # toujours dans le délai de 20 min
    clock.advance(minutes=20)
    assert not t.on_bike


def test_on_bike_delay_counts_from_last_pedaling():
    t, clock, _ = make(on_bike_delay=10)
    t.handle_data({"power": 200})
    clock.advance(minutes=2)
    t.handle_data({"power": 0})  # arrêt de pédalage, l'app envoie toujours
    clock.advance(minutes=7)
    t.handle_data({"power": 0})
    assert t.on_bike  # 9 min après le dernier coup de pédale
    clock.advance(minutes=2)
    t.handle_data({"power": 0})
    assert not t.on_bike


def test_partial_payload_keeps_other_values():
    t, _, _ = make()
    t.handle_data({"power": 180, "cadence": 85})
    t.handle_data({"heart_rate": 140})
    assert t.metric("power") == 180 and t.metric("cadence") == 85 and t.metric("heart_rate") == 140


def test_settings_changes_are_saved_and_notified():
    t, clock, saved = make(ftp=250)
    calls = []
    remove = t.add_listener(lambda: calls.append(1))
    t.handle_data({"power": 250})
    assert t.zone == 4
    t.update_settings(ftp=220)  # 250 W = 114 % de 220 W
    assert saved and saved[-1].ftp == 220
    assert t.zone == 5
    t.set_zone_color(5, "#00ff00")
    assert t.settings.zone_colors[4] == "#00FF00"
    remove()
    count = len(calls)
    t.update_settings(ftp=210)
    assert len(calls) == count


def test_tick_notifies_only_on_change():
    t, clock, _ = make(stale_timeout=5)
    calls = []
    t.add_listener(lambda: calls.append(1))
    t.handle_data({"power": 100})
    n = len(calls)
    t.tick()
    assert len(calls) == n
    clock.advance(seconds=6)
    t.tick()
    assert len(calls) == n + 1


def test_settings_from_options_tolerates_partial():
    s = Settings.from_options({"ftp": 252, "zone_colors": ["#111111"], "zone_thresholds": [76, 60]})
    assert s.ftp == 252
    assert len(s.zone_colors) == 6 and s.zone_colors[0] == "#111111"
    assert s.zone_thresholds == [60.0, 76.0, 90.0, 105.0, 119.0]  # incomplet : défauts
    s = Settings.from_options({"zone_thresholds": [76, 60, 90, 105, 119]})
    assert s.zone_thresholds[:2] == [60.0, 76.0]
    assert Settings.from_options(s.as_options()) == s


def test_hex_to_rgb():
    assert hex_to_rgb("#0078FF") == [0, 120, 255]
