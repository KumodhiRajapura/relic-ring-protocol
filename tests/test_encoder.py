import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.encoder import (
    ascii_to_codex, codex_to_ascii,
    encode_string_to_codex, decode_codex_to_string,
    convert_payload_between_codex, is_valid_codex,
    format_codex_representation
)


class TestAsciiToCodex:
    def test_h_to_base5(self):
        assert ascii_to_codex(72, 5) == [2, 4, 2]

    def test_h_to_base14(self):
        assert ascii_to_codex(72, 14) == [5, 2]

    def test_zero(self):
        assert ascii_to_codex(0, 5) == [0]

    def test_base10(self):
        assert ascii_to_codex(72, 10) == [7, 2]

    def test_invalid_codex(self):
        with pytest.raises(ValueError):
            ascii_to_codex(72, 1)


class TestCodexToAscii:
    def test_base5_to_h(self):
        assert codex_to_ascii([2, 4, 2], 5) == 72

    def test_base14_to_h(self):
        assert codex_to_ascii([5, 2], 14) == 72

    def test_invalid_digit(self):
        with pytest.raises(ValueError):
            codex_to_ascii([5, 9], 5)

    def test_roundtrip(self):
        for base in [5, 6, 8, 10, 14, 16]:
            for val in [32, 72, 101, 108, 111]:
                assert codex_to_ascii(ascii_to_codex(val, base), base) == val


class TestStringEncoding:
    def test_encode_hello(self):
        result = encode_string_to_codex("H", 5)
        assert result == [[2, 4, 2]]

    def test_decode_roundtrip(self):
        text = "Hello world"
        for base in [5, 6, 8, 14, 16]:
            encoded = encode_string_to_codex(text, base)
            decoded = decode_codex_to_string(encoded, base)
            assert decoded == text

    def test_convert_between_codex(self):
        text = "Hi"
        encoded_b5 = encode_string_to_codex(text, 5)
        converted = convert_payload_between_codex(encoded_b5, 5, 14)
        decoded = decode_codex_to_string(converted, 14)
        assert decoded == text


class TestValidation:
    def test_valid_codex(self):
        assert is_valid_codex(5) is True
        assert is_valid_codex(14) is True
        assert is_valid_codex(1) is False
        assert is_valid_codex(37) is False

    def test_format(self):
        result = format_codex_representation([[2, 4, 2], [1, 0, 0]])
        assert result == "[2,4,2] [1,0,0]"