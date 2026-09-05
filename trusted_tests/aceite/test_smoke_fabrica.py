"""Teste de aceitacao CONFIAVEL de EXEMPLO.

Vive na main protegida e e executado pela camada confiavel. Serve para (a) manter a
camada de aceitacao SEMPRE ativa (ausencia de teste = reprova) e (b) demonstrar o padrao.
SUBSTITUA por testes que exercitem, de forma caixa-preta, o que foi PEDIDO a fabrica
(ex.: chamar o CLI/funcao gerada e conferir o resultado)."""


def test_ambiente_python_sanidade():
    assert 1 + 1 == 2


def test_stdlib_disponivel():
    import hashlib
    import json

    assert hasattr(hashlib, "sha256")
    assert json.loads("[1, 2, 3]") == [1, 2, 3]
