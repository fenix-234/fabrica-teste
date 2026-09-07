"""Testes de soma e subtrai."""

from soma import soma, subtrai


def test_soma() -> None:
    assert soma(2, 3) == 5
    assert soma(-1, 1) == 0


def test_subtrai() -> None:
    assert subtrai(5, 3) == 2
    assert subtrai(0, 4) == -4
