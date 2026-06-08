# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Tests for providers.utils — normalize_name.
"""

from providers.utils import normalize_name


class TestNormalizeName:
    """Tests for normalize_name()."""

    def test_all_uppercase(self) -> None:
        assert normalize_name("YOSEMITE NATIONAL PARK") == "Yosemite National Park"

    def test_all_lowercase(self) -> None:
        assert normalize_name("yosemite national park") == "Yosemite National Park"

    def test_already_mixed_case(self) -> None:
        assert normalize_name("Yosemite National Park") == "Yosemite National Park"

    def test_mixed_case_with_mid_caps(self) -> None:
        assert normalize_name("McKinney Lake") == "McKinney Lake"

    def test_none(self) -> None:
        assert normalize_name(None) is None

    def test_empty_string(self) -> None:
        assert normalize_name("") == ""

    def test_first_word_exception(self) -> None:
        assert normalize_name("OF MICE AND MEN") == "Of Mice and Men"

    def test_inner_exceptions_lowered(self) -> None:
        assert normalize_name("THE LORD OF THE RINGS") == "The Lord of the Rings"

    def test_single_word_upper(self) -> None:
        assert normalize_name("CAMPING") == "Camping"

    def test_single_word_lower(self) -> None:
        assert normalize_name("camping") == "Camping"

    def test_single_word_mixed(self) -> None:
        assert normalize_name("Camping") == "Camping"

    def test_consecutive_spaces(self) -> None:
        assert normalize_name("YOSEMITE  NATIONAL  PARK") == "Yosemite  National  Park"

    def test_trailing_whitespace(self) -> None:
        assert normalize_name("YOSEMITE ") == "Yosemite "
