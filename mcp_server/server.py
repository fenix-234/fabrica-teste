#!/usr/bin/env python3
"""mcp_server/server.py — servidor MCP de exemplo para o repositorio fabrica-teste.

Expoe o ferramental da fabrica (factory_control/, trusted_tests/) como tools MCP, o
estado da fabrica como resources e um roteiro de revisao como prompt.

Implementa o transporte stdio do MCP — JSON-RPC 2.0 delimitado por linha — usando
apenas a biblioteca padrao. Sem dependencias: o repo continua compativel com a
politica de dependencias travadas do factory-ci, e o servidor roda sem instalar nada.

Este arquivo NAO e confiavel (nao vive em factory_control/ nem trusted_tests/): ele
apenas invoca os scripts confiaveis, nunca os substitui.

Uso: python3 mcp_server/server.py   # o host fala JSON-RPC pelo stdin/stdout
"""
import hashlib
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOME = "fabrica-teste"
VERSAO = "0.1.0"

# Revisoes do protocolo que este servidor sabe falar, da mais nova para a mais antiga.
VERSOES_SUPORTADAS = ("2025-06-18", "2025-03-26", "2024-11-05")

TIMEOUT_S = 300

# Mesmos prefixos de factory_control/validar_diff.py — replicados aqui so para leitura.
PROTEGIDOS = (".github/workflows/", ".github/codeowners", "factory_control/", "trusted_tests/")


# ---------------------------------------------------------------- infraestrutura


def _log(msg):
    """Log vai para stderr: stdout carrega exclusivamente mensagens JSON-RPC."""
    print(f"[{NOME}] {msg}", file=sys.stderr, flush=True)


def _rodar(argv, env_extra=None):
    """Executa um comando na raiz do repo e devolve (codigo, saida combinada)."""
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    try:
        r = subprocess.run(argv, cwd=RAIZ, env=env, capture_output=True, text=True,
                           timeout=TIMEOUT_S)
    except FileNotFoundError:
        return 127, f"comando nao encontrado: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"tempo esgotado apos {TIMEOUT_S}s: {' '.join(argv)}"
    return r.returncode, (r.stdout + r.stderr).strip()


def _texto(txt, erro=False):
    """Resultado de tools/call no formato do protocolo."""
    return {"content": [{"type": "text", "text": txt}], "isError": erro}


def _resultado_comando(rc, saida, rotulo):
    corpo = saida or "(sem saida)"
    return _texto(f"{rotulo}\ncodigo de saida: {rc}\n\n{corpo}", erro=rc != 0)


def _arquivos_alterados(base):
    """Nomes dos arquivos que o branch atual muda em relacao a base."""
    _rodar(["git", "fetch", "--depth=1", "origin", base])
    rc, saida = _rodar(["git", "diff", "--name-only", f"origin/{base}...HEAD"])
    if rc != 0:
        # Sem o remoto disponivel, cai para a ref local.
        rc, saida = _rodar(["git", "diff", "--name-only", f"{base}...HEAD"])
    if rc != 0:
        return None, saida
    return [l.strip() for l in saida.splitlines() if l.strip()], None


# ------------------------------------------------------------------------ tools


def _t_validar_diff(args):
    base = args.get("base", "main")
    rc, saida = _rodar([sys.executable, "factory_control/validar_diff.py"],
                       {"GITHUB_BASE_REF": base})
    return _resultado_comando(rc, saida, f"validar_diff.py (base={base})")


def _t_arquivos_protegidos(args):
    base = args.get("base", "main")
    alterados, erro = _arquivos_alterados(base)
    if alterados is None:
        return _texto(f"nao foi possivel calcular o diff contra {base}:\n{erro}", erro=True)

    linhas = [f"protegidos: {', '.join(PROTEGIDOS)}", ""]
    tocados = []
    for f in alterados:
        nl = f.replace("\\", "/").lower()
        bate = any(nl == p or nl.startswith(p) for p in PROTEGIDOS)
        if bate:
            tocados.append(f)
        linhas.append(f"  {'BLOQUEIA' if bate else 'ok      '}  {f}")

    if not alterados:
        linhas.append("  (nenhum arquivo alterado)")
    linhas.append("")
    linhas.append(f"{len(tocados)} arquivo(s) protegido(s) tocado(s) — "
                  f"{'o factory-ci vai recusar este PR' if tocados else 'o diff passa na politica'}")
    return _texto("\n".join(linhas), erro=bool(tocados))


def _t_gerar_manifesto(args):
    rc, saida = _rodar([sys.executable, "factory_control/gerar_manifesto.py"])
    return _resultado_comando(rc, saida, "gerar_manifesto.py")


def _t_testes_confiaveis(args):
    rc, saida = _rodar([sys.executable, "trusted_tests/run_trusted.py"])
    return _resultado_comando(rc, saida, "run_trusted.py")


def _t_status_fabrica(args):
    """Confere, sem rodar o CI, os pre-requisitos que o factory-ci exige."""
    checagens = [
        ("pyproject.toml", os.path.isfile(os.path.join(RAIZ, "pyproject.toml")),
         "exigido pelo passo 'dependencias travadas'"),
        ("uv.lock", os.path.isfile(os.path.join(RAIZ, "uv.lock")),
         "exigido por validar_diff.py e pelo CI"),
        ("src/", os.path.isdir(os.path.join(RAIZ, "src")), "alvo do bandit"),
        ("trusted_tests/aceite/", os.path.isdir(os.path.join(RAIZ, "trusted_tests", "aceite")),
         "sem ele run_trusted.py e no-op"),
        ("artifact-manifest.json", os.path.isfile(os.path.join(RAIZ, "artifact-manifest.json")),
         "gerado pelo build"),
    ]
    linhas = [f"  {'presente' if ok else 'AUSENTE '}  {nome:24} — {nota}"
              for nome, ok, nota in checagens]
    faltando = [n for n, ok, _ in checagens if not ok]
    linhas.append("")
    linhas.append("pronto para o factory-ci" if not faltando
                  else f"faltando: {', '.join(faltando)}")
    return _texto("\n".join(linhas))


def _t_sha256(args):
    caminho = args.get("caminho")
    if not caminho:
        return _texto("parametro obrigatorio ausente: caminho", erro=True)
    alvo = os.path.normpath(os.path.join(RAIZ, caminho))
    if not (alvo == RAIZ or alvo.startswith(RAIZ + os.sep)):
        return _texto(f"caminho fora do repositorio: {caminho}", erro=True)
    if not os.path.isfile(alvo):
        return _texto(f"arquivo nao encontrado: {caminho}", erro=True)
    with open(alvo, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return _texto(f"{digest}  {caminho}")


_BASE_SCHEMA = {
    "type": "object",
    "properties": {"base": {"type": "string",
                            "description": "branch base da comparacao (padrao: main)"}},
}

TOOLS = [
    {
        "name": "validar_diff",
        "description": ("Roda factory_control/validar_diff.py: recusa alteracao de arquivos "
                        "protegidos e dependencias git/url/path/nao-travadas. E a mesma "
                        "checagem que o factory-ci faz antes de instalar o projeto do PR."),
        "inputSchema": _BASE_SCHEMA,
        "handler": _t_validar_diff,
    },
    {
        "name": "arquivos_protegidos",
        "description": ("Lista os arquivos alterados no branch atual e marca quais caem sob "
                        "CODEOWNERS. Leitura pura — use antes de abrir um PR."),
        "inputSchema": _BASE_SCHEMA,
        "handler": _t_arquivos_protegidos,
    },
    {
        "name": "gerar_manifesto",
        "description": ("Roda factory_control/gerar_manifesto.py e escreve "
                        "artifact-manifest.json com o SHA-256 de cada arquivo em dist/ e "
                        "reports/."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _t_gerar_manifesto,
    },
    {
        "name": "testes_confiaveis",
        "description": ("Roda trusted_tests/run_trusted.py: verifica o hash dos testes de "
                        "aceitacao contra o manifesto confiavel e valida o junit resultante."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _t_testes_confiaveis,
    },
    {
        "name": "status_fabrica",
        "description": ("Confere os pre-requisitos do factory-ci (pyproject.toml, uv.lock, "
                        "src/, testes de aceitacao) sem executar o pipeline."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _t_status_fabrica,
    },
    {
        "name": "sha256",
        "description": "Calcula o SHA-256 de um arquivo do repositorio.",
        "inputSchema": {
            "type": "object",
            "properties": {"caminho": {"type": "string",
                                       "description": "caminho relativo a raiz do repo"}},
            "required": ["caminho"],
        },
        "handler": _t_sha256,
    },
]


# -------------------------------------------------------------------- resources

_POLITICA = f"""Politica da fabrica (fonte: factory_control/validar_diff.py e .github/CODEOWNERS)

Arquivos confiaveis — exigem revisao de @fenix-234 e nao podem ser alterados por PR da fabrica:
{chr(10).join('  - ' + p for p in PROTEGIDOS)}

Dependencias recusadas em pyproject.toml: git+, path local, url http(s).
uv.lock e obrigatorio: sem ele as dependencias nao estao travadas.

O CI roda em runner GitHub-hosted descartavel, com permissions: contents: read e
persist-credentials: false. Runner proprio e proibido.
"""


def _r_politica():
    return _POLITICA


def _r_manifesto():
    p = os.path.join(RAIZ, "artifact-manifest.json")
    if not os.path.isfile(p):
        return "artifact-manifest.json ainda nao foi gerado (rode a tool gerar_manifesto)."
    with open(p, encoding="utf-8") as f:
        return f.read()


def _r_workflow():
    p = os.path.join(RAIZ, ".github", "workflows", "factory-ci.yml")
    with open(p, encoding="utf-8") as f:
        return f.read()


RESOURCES = [
    {"uri": "fabrica://politica", "name": "Politica da fabrica",
     "description": "Arquivos protegidos e regras de dependencia aplicadas pelo CI.",
     "mimeType": "text/plain", "handler": _r_politica},
    {"uri": "fabrica://manifesto", "name": "artifact-manifest.json",
     "description": "Manifesto SHA-256 do ultimo build local.",
     "mimeType": "application/json", "handler": _r_manifesto},
    {"uri": "fabrica://workflow", "name": "factory-ci.yml",
     "description": "Definicao do pipeline de CI.",
     "mimeType": "text/yaml", "handler": _r_workflow},
]


# ---------------------------------------------------------------------- prompts

def _p_revisar_pr(args):
    base = args.get("base", "main")
    texto = (f"Revise o branch atual contra {base} antes de abrir o PR:\n"
             f"1. Chame arquivos_protegidos para ver se o diff toca algo sob CODEOWNERS.\n"
             f"2. Chame validar_diff para reproduzir a checagem de politica do CI.\n"
             f"3. Chame status_fabrica e aponte pre-requisitos ausentes.\n"
             f"4. Leia fabrica://politica e explique cada bloqueio encontrado, com a "
             f"correcao minima para cada um.")
    return {
        "description": f"Roteiro de revisao de politica contra {base}",
        "messages": [{"role": "user", "content": {"type": "text", "text": texto}}],
    }


PROMPTS = [
    {"name": "revisar-pr",
     "description": "Roteiro de revisao de um PR contra a politica da fabrica.",
     "arguments": [{"name": "base", "description": "branch base (padrao: main)",
                    "required": False}],
     "handler": _p_revisar_pr},
]


# ------------------------------------------------------------------- despacho

def _publico(itens, chaves):
    return [{k: v for k, v in i.items() if k in chaves} for i in itens]


def _m_initialize(params):
    pedida = params.get("protocolVersion")
    versao = pedida if pedida in VERSOES_SUPORTADAS else VERSOES_SUPORTADAS[0]
    cliente = (params.get("clientInfo") or {}).get("name", "desconhecido")
    _log(f"initialize de {cliente} — protocolo {versao}")
    return {
        "protocolVersion": versao,
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        "serverInfo": {"name": NOME, "version": VERSAO},
    }


def _m_tools_list(params):
    return {"tools": _publico(TOOLS, ("name", "description", "inputSchema"))}


def _m_tools_call(params):
    nome = params.get("name")
    for t in TOOLS:
        if t["name"] == nome:
            return t["handler"](params.get("arguments") or {})
    raise Erro(-32602, f"tool desconhecida: {nome}")


def _m_resources_list(params):
    return {"resources": _publico(RESOURCES, ("uri", "name", "description", "mimeType"))}


def _m_resources_read(params):
    uri = params.get("uri")
    for r in RESOURCES:
        if r["uri"] == uri:
            return {"contents": [{"uri": uri, "mimeType": r["mimeType"],
                                  "text": r["handler"]()}]}
    raise Erro(-32602, f"resource desconhecido: {uri}")


def _m_prompts_list(params):
    return {"prompts": _publico(PROMPTS, ("name", "description", "arguments"))}


def _m_prompts_get(params):
    nome = params.get("name")
    for p in PROMPTS:
        if p["name"] == nome:
            return p["handler"](params.get("arguments") or {})
    raise Erro(-32602, f"prompt desconhecido: {nome}")


METODOS = {
    "initialize": _m_initialize,
    "ping": lambda params: {},
    "tools/list": _m_tools_list,
    "tools/call": _m_tools_call,
    "resources/list": _m_resources_list,
    "resources/read": _m_resources_read,
    "prompts/list": _m_prompts_list,
    "prompts/get": _m_prompts_get,
}


class Erro(Exception):
    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


def _enviar(msg):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _tratar(req):
    """Devolve a resposta para uma requisicao, ou None se for notificacao."""
    ident = req.get("id")
    metodo = req.get("method")
    params = req.get("params") or {}

    if ident is None:  # notificacao: processada em silencio, sem resposta
        return None

    try:
        fn = METODOS.get(metodo)
        if fn is None:
            raise Erro(-32601, f"metodo nao suportado: {metodo}")
        return {"jsonrpc": "2.0", "id": ident, "result": fn(params)}
    except Erro as e:
        return {"jsonrpc": "2.0", "id": ident,
                "error": {"code": e.codigo, "message": e.mensagem}}
    except Exception as e:  # falha do servidor nao pode derrubar a sessao
        _log(f"erro interno em {metodo}: {e!r}")
        return {"jsonrpc": "2.0", "id": ident,
                "error": {"code": -32603, "message": f"erro interno: {e}"}}


def main():
    _log(f"escutando em stdio — raiz do repo: {RAIZ}")
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            req = json.loads(linha)
        except json.JSONDecodeError as e:
            _enviar({"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32700, "message": f"JSON invalido: {e}"}})
            continue
        resposta = _tratar(req)
        if resposta is not None:
            _enviar(resposta)
    _log("stdin fechou — encerrando")


if __name__ == "__main__":
    main()
