"""Unit tests for GreeMQTT.config module."""

import os
import pytest
from unittest.mock import patch

# Mock the required environment variables before importing config
with patch.dict(os.environ, {"MQTT_BROKER": "test_broker"}):
    from GreeMQTT.config import get_env_list, get_env_int, get_env_bool, get_env_str


class TestGetEnvList:
    """Test cases for get_env_list function."""

    def test_get_env_list_with_comma_separated_values(self):
        """Test parsing comma-separated environment variable values."""
        with patch.dict(os.environ, {"TEST_VAR": "value1,value2,value3"}):
            result = get_env_list("TEST_VAR")
            assert result == ["value1", "value2", "value3"]

    def test_get_env_list_with_spaces_in_values(self):
        """Test parsing values with leading/trailing spaces."""
        with patch.dict(os.environ, {"TEST_VAR": " value1 , value2 , value3 "}):
            result = get_env_list("TEST_VAR")
            assert result == ["value1", "value2", "value3"]

    def test_get_env_list_with_empty_values(self):
        """Test filtering out empty values."""
        with patch.dict(os.environ, {"TEST_VAR": "value1,,value2,   ,value3"}):
            result = get_env_list("TEST_VAR")
            assert result == ["value1", "value2", "value3"]

    def test_get_env_list_with_single_value(self):
        """Test single value without commas."""
        with patch.dict(os.environ, {"TEST_VAR": "single_value"}):
            result = get_env_list("TEST_VAR")
            assert result == ["single_value"]

    def test_get_env_list_with_default_when_var_not_set(self):
        """Test using default value when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_list("NONEXISTENT_VAR", "default1,default2")
            assert result == ["default1", "default2"]

    def test_get_env_list_with_none_default_when_var_not_set(self):
        """Test returning empty list when variable not set and no default."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_list("NONEXISTENT_VAR")
            assert result == []

    def test_get_env_list_with_empty_string(self):
        """Test handling empty string environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            result = get_env_list("TEST_VAR")
            assert result == []

    def test_get_env_list_with_whitespace_only(self):
        """Test handling whitespace-only environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "   "}):
            result = get_env_list("TEST_VAR")
            assert result == []


class TestGetEnvInt:
    """Test cases for get_env_int function."""

    def test_get_env_int_with_valid_integer(self):
        """Test parsing valid integer values."""
        with patch.dict(os.environ, {"TEST_VAR": "42"}):
            result = get_env_int("TEST_VAR")
            assert result == 42

    def test_get_env_int_with_negative_integer(self):
        """Test parsing negative integer values."""
        with patch.dict(os.environ, {"TEST_VAR": "-10"}):
            result = get_env_int("TEST_VAR")
            assert result == -10

    def test_get_env_int_with_zero(self):
        """Test parsing zero value."""
        with patch.dict(os.environ, {"TEST_VAR": "0"}):
            result = get_env_int("TEST_VAR")
            assert result == 0

    def test_get_env_int_with_default_when_var_not_set(self):
        """Test using default value when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_int("NONEXISTENT_VAR", 100)
            assert result == 100

    def test_get_env_int_raises_error_when_var_not_set_no_default(self):
        """Test raising error when variable not set and no default provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="NONEXISTENT_VAR environment variable is not set"):
                get_env_int("NONEXISTENT_VAR")

    def test_get_env_int_raises_error_with_invalid_integer(self):
        """Test raising error with non-integer values."""
        with patch.dict(os.environ, {"TEST_VAR": "not_an_integer"}):
            with pytest.raises(ValueError, match="TEST_VAR must be an integer"):
                get_env_int("TEST_VAR")

    def test_get_env_int_raises_error_with_float(self):
        """Test raising error with float values."""
        with patch.dict(os.environ, {"TEST_VAR": "3.14"}):
            with pytest.raises(ValueError, match="TEST_VAR must be an integer"):
                get_env_int("TEST_VAR")

    def test_get_env_int_raises_error_with_empty_string(self):
        """Test raising error with empty string."""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            with pytest.raises(ValueError, match="TEST_VAR must be an integer"):
                get_env_int("TEST_VAR")


class TestGetEnvBool:
    """Test cases for get_env_bool function."""

    def test_get_env_bool_with_true_lowercase(self):
        """Test parsing 'true' value."""
        with patch.dict(os.environ, {"TEST_VAR": "true"}):
            result = get_env_bool("TEST_VAR")
            assert result is True

    def test_get_env_bool_with_true_uppercase(self):
        """Test parsing 'TRUE' value."""
        with patch.dict(os.environ, {"TEST_VAR": "TRUE"}):
            result = get_env_bool("TEST_VAR")
            assert result is True

    def test_get_env_bool_with_true_mixed_case(self):
        """Test parsing 'True' value."""
        with patch.dict(os.environ, {"TEST_VAR": "True"}):
            result = get_env_bool("TEST_VAR")
            assert result is True

    def test_get_env_bool_with_true_and_whitespace(self):
        """Test parsing 'true' with leading/trailing whitespace."""
        with patch.dict(os.environ, {"TEST_VAR": "  true  "}):
            result = get_env_bool("TEST_VAR")
            assert result is True

    def test_get_env_bool_with_false_values(self):
        """Test parsing various false values."""
        false_values = ["false", "False", "FALSE", "no", "0", ""]
        for value in false_values:
            with patch.dict(os.environ, {"TEST_VAR": value}):
                result = get_env_bool("TEST_VAR")
                assert result is False, f"Failed for value: {value}"

    def test_get_env_bool_with_default_true_when_var_not_set(self):
        """Test using True default when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_bool("NONEXISTENT_VAR", True)
            assert result is True

    def test_get_env_bool_with_default_false_when_var_not_set(self):
        """Test using False default when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_bool("NONEXISTENT_VAR", False)
            assert result is False

    def test_get_env_bool_with_no_default_when_var_not_set(self):
        """Test default False when no default provided and variable not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_bool("NONEXISTENT_VAR")
            assert result is False


class TestGetEnvStr:
    """Test cases for get_env_str function."""

    def test_get_env_str_with_valid_string(self):
        """Test retrieving valid string value."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = get_env_str("TEST_VAR")
            assert result == "test_value"

    def test_get_env_str_with_empty_string(self):
        """Test retrieving empty string value."""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            result = get_env_str("TEST_VAR")
            assert result == ""

    def test_get_env_str_with_whitespace_only(self):
        """Test retrieving whitespace-only string."""
        with patch.dict(os.environ, {"TEST_VAR": "   "}):
            result = get_env_str("TEST_VAR")
            assert result == "   "

    def test_get_env_str_with_special_characters(self):
        """Test retrieving string with special characters."""
        special_value = "test@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        with patch.dict(os.environ, {"TEST_VAR": special_value}):
            result = get_env_str("TEST_VAR")
            assert result == special_value

    def test_get_env_str_with_default_when_var_not_set(self):
        """Test using default value when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_str("NONEXISTENT_VAR", "default_value")
            assert result == "default_value"

    def test_get_env_str_with_none_default_when_var_not_set(self):
        """Test returning None when variable not set and no default."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_str("NONEXISTENT_VAR")
            assert result is None

    def test_get_env_str_with_required_flag_success(self):
        """Test required flag with variable set."""
        with patch.dict(os.environ, {"TEST_VAR": "required_value"}):
            result = get_env_str("TEST_VAR", required=True)
            assert result == "required_value"

    def test_get_env_str_with_required_flag_raises_error_when_not_set(self):
        """Test required flag raises error when variable not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="NONEXISTENT_VAR environment variable is required"):
                get_env_str("NONEXISTENT_VAR", required=True)

    def test_get_env_str_with_required_flag_raises_error_when_empty(self):
        """Test required flag raises error when variable is empty."""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            with pytest.raises(ValueError, match="TEST_VAR environment variable is required"):
                get_env_str("TEST_VAR", required=True)

    def test_get_env_str_with_required_flag_and_default(self):
        """Test required flag with default value when variable not set - should not raise error."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_str("NONEXISTENT_VAR", "default", required=True)
            assert result == "default"

    def test_get_env_str_with_unicode_characters(self):
        """Test retrieving string with unicode characters."""
        unicode_value = "测试值 🚀 αβγ"
        with patch.dict(os.environ, {"TEST_VAR": unicode_value}):
            result = get_env_str("TEST_VAR")
            assert result == unicode_value