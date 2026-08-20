"""Testes da funcao soma."""

from soma import soma


def test_soma_positivos() -> None:
    assert soma(2, 3) == 5


def test_soma_negativos() -> None:
    assert soma(-1, -4) == -5


def test_soma_zero() -> None:
    assert soma(0, 0) == 0
