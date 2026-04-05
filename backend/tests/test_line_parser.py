"""Tests for LINE text message parser (Story 9.2)."""

from __future__ import annotations

from domains.line.parser import parse_order_text


def test_parse_x_separator():
    result = parse_order_text("商品A x 3, 商品B x 5")
    assert len(result) == 2
    assert result[0].product_query == "商品A"
    assert result[0].quantity == 3
    assert result[1].product_query == "商品B"
    assert result[1].quantity == 5


def test_parse_space_newline_separator():
    result = parse_order_text("ProductA 3\nProductB 5")
    assert len(result) == 2
    assert result[0].product_query == "ProductA"
    assert result[0].quantity == 3


def test_parse_equals_separator():
    result = parse_order_text("商品A=3, 商品B=5")
    assert len(result) == 2
    assert result[0].product_query == "商品A"
    assert result[0].quantity == 3


def test_parse_colon_separator():
    result = parse_order_text("商品A:3")
    assert len(result) == 1
    assert result[0].quantity == 3


def test_parse_asterisk_separator():
    result = parse_order_text("商品A*3")
    assert len(result) == 1
    assert result[0].quantity == 3


def test_parse_quantity_first_chinese():
    result = parse_order_text("3個商品A, 5個商品B")
    assert len(result) == 2
    assert result[0].product_query == "商品A"
    assert result[0].quantity == 3
    assert result[1].product_query == "商品B"
    assert result[1].quantity == 5


def test_parse_no_space_before_digit():
    result = parse_order_text("ProductA x3")
    assert len(result) == 1
    assert result[0].product_query == "ProductA"
    assert result[0].quantity == 3


def test_parse_empty_text():
    assert parse_order_text("") == []
    assert parse_order_text("   ") == []


def test_parse_garbage_text():
    assert parse_order_text("hello world") == []


def test_parse_quantity_zero_skipped():
    result = parse_order_text("商品A x 0")
    assert result == []
