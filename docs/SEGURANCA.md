# Modelo de segurança da fábrica

Este repositório roda código gerado automaticamente (PRs do robô `fabrica-neural-fenix`).
O objetivo dos controles é: **rodar esse código não-confiável sem que ele possa mentir
sobre a própria qualidade nem alterar as regras que o julgam.**

## Princípio central

> O inspetor (as verificações) roda a partir da **main confiável**, nunca da cópia do PR.
> Quem está sendo julgado não segura a régua.

## Como funciona (dois estágios)

1. **`factory-ci` (Estágio A — bancada NÃO confiável).** Dispara no PR. Instala, testa e
   constrói o código proposto, isolado, com token somente-leitura e sem segredos. O
   resultado dele é **informativo** — não vale como aprovação.

2. **`factory-verify` (Estágio B — veredito CONFIÁVEL).** Dispara depois, via
   `workflow_run`, que **sempre executa a versão da main**. O PR não consegue reescrever
   este estágio. Aqui a política do diff é **autoritativa e falha-fechado**: bloqueia
   qualquer alteração em arquivos protegidos (`.github/workflows/`, `.github/CODEOWNERS`,
   `factory_control/`, `trusted_tests/`) e dependências não-fixadas (em `pyproject.toml`
   **e** `uv.lock`). Publica o status **`fabrica/verificacao-confiavel`** no commit.

## Regras que tornam isto sólido (falha-fechado)

- **`validar_diff.py`**: se qualquer comando de git falhar, **bloqueia** (nunca "passa por
  erro"). Usa histórico completo (sem `--depth=1`, que mascarava mudanças).
- **`run_trusted.py`**: **exige** que existam testes de aceitação e um manifesto de
  integridade; verifica o hash de cada teste. Ausência de teste/manifesto = **reprova**
  (antes era "ok, no-op").
- **`gerar_manifesto.py`**: não vaza caminhos internos do runner.

## O que VOCÊ precisa configurar no GitHub (não é código)

1. Proteção da `main` com **"Require review from Code Owners"** e
   **"Do not allow bypassing / Include administrators"** ligado.
2. Marcar **`fabrica/verificacao-confiavel`** como **status check obrigatório** para merge.
3. App `fabrica-neural-fenix` **sem** escrita direta na `main` (só abrir PR).

## Escrevendo os testes de aceitação reais

`trusted_tests/aceite/test_smoke_fabrica.py` é um **exemplo** (mantém a camada ativa).
Substitua por testes que exercitem, de forma caixa-preta, o que foi **pedido** à fábrica.
Ao adicionar/alterar testes, atualize `trusted_tests/manifesto.json` com os novos hashes.

## Limite conhecido (honesto)

O veredito confiável garante que o PR **não alterou** as regras nem os testes confiáveis,
e que a política do diff é inviolável pelo PR. A execução dos testes de aceitação ainda
ocorre no Estágio A; um gerador totalmente adversário poderia, em tese, forjar o relatório
desses testes — cenário improvável aqui (a fábrica é sua) e barrado, no fim, pela sua
revisão obrigatória antes do merge. Atestação criptográfica de execução é uma evolução
futura, se algum dia for necessária.
