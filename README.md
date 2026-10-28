# HomeTrainer To Home Assistant — intégration Home Assistant

Intégration Home Assistant pour un home trainer connecté (Wahoo KICKR, ou tout
home trainer Bluetooth FTMS / Cycling Power). Une app iOS lit le home trainer en
Bluetooth et envoie ses mesures à Home Assistant par **webhook** ; l'intégration
crée un **appareil** avec ses capteurs, calcule la zone de puissance et la
présence « sur le vélo », et garde les réglages (FTP, couleurs des zones, délai).

L'app iOS compagnon : [hometrainer-to-home-assistant](https://github.com/lobwick/hometrainer-to-home-assistant) (HomeTrainerHA).

## Entités

| Entité | Description |
|---|---|
| `sensor.<nom>_power` | Puissance instantanée (W) |
| `sensor.<nom>_power_3s` | Puissance lissée sur 3 s (W) |
| `sensor.<nom>_cadence` | Cadence (rpm) |
| `sensor.<nom>_speed` | Vitesse (km/h) |
| `sensor.<nom>_heart_rate` | Fréquence cardiaque (bpm), si disponible |
| `sensor.<nom>_distance` | Distance de la séance |
| `sensor.<nom>_energy` | Énergie de la séance (kcal) |
| `sensor.<nom>_ftp_percent` | Puissance lissée en % de la FTP |
| `sensor.<nom>_power_zone` | Zone 0 (arrêt) à 6, attributs `zone_name`, `hex_color`, `rgb_color`, `power_min`, `power_max` |
| `binary_sensor.<nom>_on_bike` | Sur le vélo : pendant le pédalage et jusqu'au délai réglé après le dernier coup de pédale |
| `binary_sensor.<nom>_app_connected` | L'app envoie des données (diagnostic) |
| `number.<nom>_ftp` | FTP (réglage) |
| `number.<nom>_on_bike_delay` | Délai « sur le vélo » en minutes (réglage) |
| `text.<nom>_zone_N_colour` | Couleur de la zone N au format `#RRGGBB` (réglage) |

Sans données pendant 5 s (réglable), puissance, cadence et vitesse repassent à 0
et la zone à 0 : les entités ne disparaissent jamais.

Zones (bornes basses en % de la FTP, découpage Zwift, réglables via
**Configurer**) : Z1 < 60 % ≤ Z2 < 76 % ≤ Z3 < 90 % ≤ Z4 < 105 % ≤ Z5 < 119 % ≤ Z6.

## Installation (HACS)

1. HACS → menu ⋮ → **Dépôts personnalisés** → ajouter l'URL de ce dépôt, catégorie *Intégration*.
2. Installer **HomeTrainer To Home Assistant**, redémarrer Home Assistant.
3. Paramètres → Appareils et services → **Ajouter une intégration** → *HomeTrainer To Home Assistant*.
4. Copier l'adresse du webhook affichée dans l'app iOS (Réglages → Adresse du webhook).
   Elle reste consultable via le bouton **Configurer** de l'intégration.

## Format envoyé par l'app

`POST /api/webhook/<id>` en JSON, toutes les clés sont optionnelles :

```json
{"power": 245, "cadence": 91, "speed": 34.8, "heart_rate": 148,
 "distance": 12450, "energy": 310, "device": "KICKR CORE 1234"}
```

`{"test": true}` vérifie la connexion sans modifier les mesures. La réponse
contient `ok`, `on_bike`, `zone` et `ftp`.

## Exemple d'automatisation

```yaml
triggers:
  - trigger: state
    entity_id: sensor.home_trainer_power_zone
    to: ["1", "2", "3", "4", "5", "6"]
    for: { seconds: 1 }
actions:
  - action: light.turn_on
    target: { area_id: bureau }
    data:
      rgb_color: "{{ state_attr('sensor.home_trainer_power_zone', 'rgb_color') }}"
```

## Tests

```bash
pip install -r requirements_test.txt
pytest
```
