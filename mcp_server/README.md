# Servidor MCP de exemplo — fabrica-teste

Expõe o ferramental da fábrica como um servidor MCP: as checagens de política que hoje
só rodam dentro do `factory-ci` passam a ser chamáveis por um assistente durante o
desenvolvimento, antes de abrir o PR.

Implementa o transporte **stdio** (JSON-RPC 2.0 delimitado por linha) usando apenas a
biblioteca padrão. Sem dependências — o repositório continua compatível com a política
de dependências travadas, e o servidor roda sem instalar nada.

## Instalação

O `.mcp.json` na raiz já registra o servidor no escopo do projeto: o Claude Code o
encontra sozinho ao abrir o repo (pede aprovação na primeira vez). Para registrar
manualmente:

```bash
claude mcp add fabrica -- python3 mcp_server/server.py
claude mcp list          # confere o estado da conexão
```

Dentro da sessão, `/mcp` mostra as conexões ativas. As tools chegam ao modelo como
`mcp__fabrica__<nome>`.

## Tools

| Tool | O que faz |
|---|---|
| `validar_diff` | Roda `factory_control/validar_diff.py` — a mesma checagem que o CI faz antes de instalar o projeto do PR |
| `arquivos_protegidos` | Lista os arquivos alterados e marca quais caem sob CODEOWNERS (leitura pura) |
| `gerar_manifesto` | Roda `factory_control/gerar_manifesto.py` e escreve `artifact-manifest.json` |
| `testes_confiaveis` | Roda `trusted_tests/run_trusted.py` |
| `status_fabrica` | Confere os pré-requisitos do `factory-ci` sem executar o pipeline |
| `sha256` | Hash de um arquivo do repositório |

## Resources

| URI | Conteúdo |
|---|---|
| `fabrica://politica` | Arquivos protegidos e regras de dependência aplicadas pelo CI |
| `fabrica://manifesto` | `artifact-manifest.json` do último build local |
| `fabrica://workflow` | Definição do `factory-ci.yml` |

## Prompts

`revisar-pr` — roteiro de revisão de um PR contra a política da fábrica. Aceita o
argumento opcional `base` (padrão: `main`).

## Testes

```bash
python3 mcp_server/smoke_test.py
```

Sobe o servidor como subprocesso e exercita o transporte stdio real: handshake,
descoberta, execução de tools, leitura de resources e prompts, e o tratamento de erros
(método desconhecido, tool inexistente, JSON inválido).

## Limites de confiança

Este diretório **não** é confiável: não vive em `factory_control/` nem em
`trusted_tests/`, e por isso um PR pode alterá-lo sem revisão de CODEOWNERS. O servidor
apenas invoca os scripts confiáveis como subprocessos — nunca os substitui, e o
resultado que ele reporta não tem valor de atestado. A palavra final continua sendo a
execução dentro do `factory-ci`, em runner descartável.

A tool `sha256` restringe o caminho à raiz do repositório; todas as chamadas de
subprocesso usam argv fixo, sem shell.
