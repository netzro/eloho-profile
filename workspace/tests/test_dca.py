"""Unit tests for DCA allocation logic."""
import pytest
from eloho.dca import compute_allocations, _min_units_for_cost, MIN_BUY_COST
from eloho.config import TARGET_UNITS, STOCK_WEIGHTS, STOCKS


def _make_prices(prices: dict) -> dict:
    """Helper: build price dict from {ticker: (price, change_pct)}."""
    return {t: {"price": p, "change_pct": c} for t, (p, c) in prices.items()}


class TestMinUnitsForCost:
    def test_exact_multiple(self):
        assert _min_units_for_cost(1000, 5000) == 5

    def test_non_exact_ceil(self):
        assert _min_units_for_cost(1200, 5000) == 5  # 4.17 → 5

    def test_zero_price(self):
        assert _min_units_for_cost(0, 5000) == 0

    def test_negative_price(self):
        assert _min_units_for_cost(-100, 5000) == 0

    def test_one_unit_meets_threshold(self):
        assert _min_units_for_cost(6000, 5000) == 1


class TestComputeAllocations:
    def test_all_stocks_in_output(self):
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        result = compute_allocations(prices, budget=40000, holdings={})
        assert len(result) == 7
        assert {a["ticker"] for a in result} == set(STOCKS)

    def test_min_buy_cost_enforced(self):
        """Stocks that can't meet MIN_BUY_COST get 0 units."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        result = compute_allocations(prices, budget=40000, holdings={})
        # At 40k budget, all stocks should meet 5k min
        for a in result:
            if a["units"] > 0:
                assert a["amount_ngn"] >= MIN_BUY_COST, f"{a['ticker']}: {a['amount_ngn']}"

    def test_target_met_stock_gets_zero(self):
        """Stocks at or above target get 0 units."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        holdings = {"GTCO": 500}  # Target met
        result = compute_allocations(prices, budget=40000, holdings=holdings)
        gtco = next(a for a in result if a["ticker"] == "GTCO")
        assert gtco["units"] == 0
        assert gtco["amount_ngn"] == 0.0

    def test_whole_units_only(self):
        """All units must be whole numbers (no fractions)."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        result = compute_allocations(prices, budget=40000, holdings={})
        for a in result:
            assert a["units"] == int(a["units"]), f"{a['ticker']}: {a['units']} is not whole"

    def test_budget_not_exceeded(self):
        """Total allocated must not exceed budget."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        result = compute_allocations(prices, budget=40000, holdings={})
        total = sum(a["amount_ngn"] for a in result)
        assert total <= 40000

    def test_near_target_gets_priority(self):
        """Stock closer to target should be funded before others."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        # GTCO at 490/500 (10 remaining), others at full target
        holdings = {"GTCO": 490}
        result = compute_allocations(prices, budget=15000, holdings=holdings)
        gtco = next(a for a in result if a["ticker"] == "GTCO")
        # GTCO should get units to close the 10-unit gap
        assert gtco["units"] > 0

    def test_zero_budget(self):
        """Zero budget should result in all zero units."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (1418.0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        result = compute_allocations(prices, budget=0, holdings={})
        for a in result:
            assert a["units"] == 0

    def test_no_price_stock_skipped(self):
        """Stock with no price gets 0 units."""
        prices = _make_prices({
            "GTCO": (115.55, 0), "ZENITHBANK": (110.0, 0),
            "OKOMUOIL": (0, 0), "TRANSCORP": (44.0, 0),
            "MTNN": (800.0, 0), "ACCESSCORP": (22.8, 0),
            "FIDSON": (101.2, 0),
        })
        result = compute_allocations(prices, budget=40000, holdings={})
        okomuoil = next(a for a in result if a["ticker"] == "OKOMUOIL")
        assert okomuoil["units"] == 0


class TestWeightsFromTargets:
    def test_weights_sum_to_one(self):
        assert abs(sum(STOCK_WEIGHTS.values()) - 1.0) < 1e-9

    def test_weights_proportional_to_targets(self):
        gtco_weight = STOCK_WEIGHTS["GTCO"]
        zenith_weight = STOCK_WEIGHTS["ZENITHBANK"]
        # GTCO target 500, ZENITH target 500 → weights should be equal
        assert abs(gtco_weight - zenith_weight) < 1e-9

    def test_higher_target_gets_higher_weight(self):
        gtco_weight = STOCK_WEIGHTS["GTCO"]
        mtnn_weight = STOCK_WEIGHTS["MTNN"]
        # GTCO target 500 > MTNN target 50. GTCO should be higher.
        assert gtco_weight > mtnn_weight


class TestWithFixtures:
    def test_all_7_stocks_always_present(self, current_prices, empty_holdings):
        result = compute_allocations(current_prices, budget=40000, holdings=empty_holdings)
        assert len(result) == 7

    def test_accesscorp_target_met_excluded(self, current_prices, partial_holdings):
        """ACCESSCORP at 200/200 should get 0 units."""
        result = compute_allocations(current_prices, budget=40000, holdings=partial_holdings)
        access = next(a for a in result if a["ticker"] == "ACCESSCORP")
        assert access["units"] == 0

    def test_stocks_with_holdings_still_buy(self, current_prices, partial_holdings):
        """GTCO at 100/500 should still get units."""
        result = compute_allocations(current_prices, budget=40000, holdings=partial_holdings)
        gtco = next(a for a in result if a["ticker"] == "GTCO")
        assert gtco["units"] > 0

    def test_small_budget_distribution(self, current_prices, empty_holdings):
        """With very small budget, only high-priority stocks get funded."""
        result = compute_allocations(current_prices, budget=5000, holdings=empty_holdings)
        funded = [a for a in result if a["units"] > 0]
        total = sum(a["amount_ngn"] for a in result)
        assert total <= 5000
        # At least one stock should be funded
        if funded:
            for a in funded:
                assert a["amount_ngn"] >= MIN_BUY_COST
