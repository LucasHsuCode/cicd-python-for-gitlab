"""Test
unit test example
"""
import pytest
from examples.example import aaa


@pytest.fixture
def order():
    """order
    """
    return []


@pytest.fixture
def order_a(order):
    """order_a
    """
    order.append("a")


@pytest.fixture
def order_b(order_a, order):
    """order_b
    """
    order.append("b")


@pytest.fixture(autouse=True)
def order_c(order_b, order):
    """order_c
    """
    order.append("c")


@pytest.fixture
def order_d(order_b, order):
    """order_d
    """
    order.append("d")


@pytest.fixture
def order_e(order_d, order):
    """order_e
    """
    order.append("e")


@pytest.fixture
def order_f(order_e, order):
    """order_f
    """
    order.append("f")


@pytest.fixture
def order_g(order_f, order_c, order):
    """order_g
    """
    order.append("g")


def test_order_and_g(order_g, order):
    """test_order_and_g
    """
    assert order == ["a", "b", "c", "d", "e", "f", "g"]


def test_aaa():
    """test_aaa
    """
    assert aaa() == 3
