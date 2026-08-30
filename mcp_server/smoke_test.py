#!/usr/bin/env python3
"""mcp_server/smoke_test.py — exercita o servidor MCP pelo transporte stdio real.

Sobe server.py como subprocesso, faz o handshake e chama cada metodo, conferindo o
formato das respostas. Sem dependencias: python3 mcp_server/smoke_test.py
"""
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SERVIDOR = os.path.join(AQUI, "server.py")

falhas = []


def checar(condicao, descricao):
    print(f"  {'ok  ' if condicao else 'FALHA'}  {descricao}")
    if not condicao:
        falhas.append(descricao)


def main():
    proc = subprocess.Popen([sys.executable, SERVIDOR], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            bufsize=1)
    prox = [0]

    def pedir(metodo, params=None, notificacao=False):
        msg = {"jsonrpc": "2.0", "method": metodo, "params": params or {}}
        if not notificacao:
            prox[0] += 1
            msg["id"] = prox[0]
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        if notificacao:
            return None
        return json.loads(proc.stdout.readline())

    try:
        print("handshake")
        r = pedir("initialize", {"protocolVersion": "2025-06-18",
                                 "capabilities": {},
                                 "clientInfo": {"name": "smoke_test", "version": "0"}})
        checar(r["result"]["protocolVersion"] == "2025-06-18", "versao do protocolo ecoada")
        checar(r["result"]["serverInfo"]["name"] == "fabrica-teste", "serverInfo presente")
        checar(set(r["result"]["capabilities"]) == {"tools", "resources", "prompts"},
               "capacidades anunciadas")
        pedir("notifications/initialized", notificacao=True)

        print("descoberta")
        tools = pedir("tools/list")["result"]["tools"]
        checar(len(tools) == 6, f"6 tools listadas (vieram {len(tools)})")
        checar(all({"name", "description", "inputSchema"} <= set(t) for t in tools),
               "toda tool tem nome, descricao e schema")
        checar(all("handler" not in t for t in tools), "handler nao vaza no protocolo")
        recursos = pedir("resources/list")["result"]["resources"]
        checar(len(recursos) == 3, f"3 resources listados (vieram {len(recursos)})")
        prompts = pedir("prompts/list")["result"]["prompts"]
        checar(len(prompts) == 1, f"1 prompt listado (vieram {len(prompts)})")

        print("execucao")
        r = pedir("tools/call", {"name": "status_fabrica", "arguments": {}})
        checar(r["result"]["content"][0]["type"] == "text", "status_fabrica devolve texto")
        r = pedir("tools/call", {"name": "sha256", "arguments": {"caminho": "README.md"}})
        checar(not r["result"]["isError"] and len(r["result"]["content"][0]["text"].split()[0]) == 64,
               "sha256 do README tem 64 hex")
        r = pedir("tools/call", {"name": "sha256", "arguments": {"caminho": "../../etc/passwd"}})
        checar(r["result"]["isError"], "sha256 recusa caminho fora do repo")
        r = pedir("tools/call", {"name": "sha256", "arguments": {}})
        checar(r["result"]["isError"], "sha256 recusa parametro ausente")
        r = pedir("tools/call", {"name": "arquivos_protegidos", "arguments": {"base": "main"}})
        checar("protegidos:" in r["result"]["content"][0]["text"], "arquivos_protegidos responde")

        print("resources e prompts")
        r = pedir("resources/read", {"uri": "fabrica://politica"})
        checar("CODEOWNERS" in r["result"]["contents"][0]["text"], "politica legivel")
        r = pedir("resources/read", {"uri": "fabrica://workflow"})
        checar("factory-ci" in r["result"]["contents"][0]["text"], "workflow legivel")
        r = pedir("prompts/get", {"name": "revisar-pr", "arguments": {"base": "main"}})
        checar(r["result"]["messages"][0]["role"] == "user", "prompt devolve mensagens")

        print("erros")
        checar(pedir("metodo/inexistente")["error"]["code"] == -32601, "metodo desconhecido -> -32601")
        checar(pedir("tools/call", {"name": "nao_existe"})["error"]["code"] == -32602,
               "tool desconhecida -> -32602")
        checar(pedir("resources/read", {"uri": "fabrica://nada"})["error"]["code"] == -32602,
               "resource desconhecido -> -32602")
        proc.stdin.write("isto nao e json\n")
        proc.stdin.flush()
        checar(json.loads(proc.stdout.readline())["error"]["code"] == -32700,
               "linha invalida -> -32700 sem derrubar a sessao")
        checar(pedir("ping")["result"] == {}, "ping responde depois do erro de parse")
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)

    print()
    if falhas:
        print(f"{len(falhas)} falha(s): " + "; ".join(falhas))
        sys.exit(1)
    print("todas as checagens passaram")


if __name__ == "__main__":
    main()
