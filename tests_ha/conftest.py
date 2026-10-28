"""Active l'intégration personnalisée dans le Home Assistant de test."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Autorise le chargement de custom_components/hometrainer."""
    yield
