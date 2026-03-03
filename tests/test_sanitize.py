"""Tests for input sanitization — Phase F5 validation."""

import pytest

from quantproto.mcp.sanitize import (
    validate_prices_input,
    validate_returns_input,
    validate_positive_int,
    validate_confidence,
    validate_weights,
)


class TestValidatePricesInput:
    def test_valid(self):
        validate_prices_input({"A": [1.0, 2.0, 3.0]})

    def test_not_dict(self):
        with pytest.raises(ValueError, match="Expected dict"):
            validate_prices_input([1, 2, 3])

    def test_empty(self):
        with pytest.raises(ValueError, match="Empty"):
            validate_prices_input({})

    def test_non_string_key(self):
        with pytest.raises(ValueError, match="Ticker must be str"):
            validate_prices_input({123: [1.0]})

    def test_non_list_values(self):
        with pytest.raises(ValueError, match="must be list"):
            validate_prices_input({"A": 1.0})

    def test_empty_values(self):
        with pytest.raises(ValueError, match="Empty values"):
            validate_prices_input({"A": []})

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="Non-numeric"):
            validate_prices_input({"A": ["not_a_number"]})

    def test_too_many_points(self):
        with pytest.raises(ValueError, match="Too many"):
            validate_prices_input({"A": list(range(10_001))})


class TestValidateReturnsInput:
    def test_valid(self):
        validate_returns_input([0.01, -0.02, 0.03])

    def test_not_list(self):
        with pytest.raises(ValueError, match="Expected list"):
            validate_returns_input("string")

    def test_empty(self):
        with pytest.raises(ValueError, match="Empty"):
            validate_returns_input([])

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="Non-numeric"):
            validate_returns_input([0.01, "bad"])


class TestValidatePositiveInt:
    def test_valid(self):
        validate_positive_int(20, "lookback")

    def test_zero(self):
        with pytest.raises(ValueError, match=">= 1"):
            validate_positive_int(0, "lookback")

    def test_negative(self):
        with pytest.raises(ValueError, match=">= 1"):
            validate_positive_int(-5, "lookback")

    def test_too_large(self):
        with pytest.raises(ValueError, match="<="):
            validate_positive_int(300, "lookback", max_val=252)

    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="must be int"):
            validate_positive_int(True, "flag")


class TestValidateConfidence:
    def test_valid(self):
        validate_confidence(0.95)

    def test_zero(self):
        with pytest.raises(ValueError, match="\\(0, 1\\)"):
            validate_confidence(0.0)

    def test_one(self):
        with pytest.raises(ValueError, match="\\(0, 1\\)"):
            validate_confidence(1.0)

    def test_greater_than_one(self):
        with pytest.raises(ValueError):
            validate_confidence(1.5)


class TestValidateWeights:
    def test_valid(self):
        validate_weights({"mom": 0.5, "mr": 0.5})

    def test_not_dict(self):
        with pytest.raises(ValueError, match="must be dict"):
            validate_weights([0.5])

    def test_negative_weight(self):
        with pytest.raises(ValueError, match=">= 0"):
            validate_weights({"mom": -0.5})
