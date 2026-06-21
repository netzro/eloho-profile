"""Shared test fixtures."""
import pytest
from eloho.config import STOCKS


@pytest.fixture
def current_prices():
    """Realistic current prices for all 7 stocks."""
    return {
        "GTCO": {"price": 115.55, "change_pct": -9.97},
        "ZENITHBANK": {"price": 110.00, "change_pct": -4.76},
        "OKOMUOIL": {"price": 1418.00, "change_pct": 0.0},
        "TRANSCORP": {"price": 44.00, "change_pct": 0.0},
        "MTNN": {"price": 800.00, "change_pct": 0.0},
        "ACCESSCORP": {"price": 22.80, "change_pct": -0.87},
        "FIDSON": {"price": 101.20, "change_pct": 0.0},
    }


@pytest.fixture
def empty_holdings():
    return {}


@pytest.fixture
def partial_holdings():
    """Some stocks partially filled."""
    return {
        "GTCO": 100,
        "ZENITHBANK": 50,
        "ACCESSCORP": 200,  # Target met
    }
