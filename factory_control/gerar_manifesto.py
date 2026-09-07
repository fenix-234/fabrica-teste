"""factory_control/gerar_manifesto.py — gera artifact-manifest.json com SHA-256 de cada
arquivo publicado (dist/ e reports/). Registra commit, workflow run e repo. Nao inclui
caminhos internos do runner. Arquivo CONFIAVEL (main)."""
import hashlib
import json
import os


def _walk(base):
    saida = {}
    if not os.path.isdir(base):
        return saida
    for raiz, _, arqs in os.walk(base):
        for a in arqs:
            p = os.path.join(raiz, a)
            with open(p, "rb") as f:
                saida[os.path.relpath(p).replace("\\", "/")] = hashlib.sha256(f.read()).hexdigest()
    return saida


def main():
    arquivos = {}
    for base in ("dist", "reports"):
        arquivos.update(_walk(base))
    manifesto = {
        "commit": os.environ.get("GITHUB_SHA", ""),
        "workflow_run": os.environ.get("GITHUB_RUN_ID", ""),
        "repo": os.environ.get("GITHUB_REPOSITORY", ""),
        "arquivos_sha256": arquivos,
        "total": len(arquivos),
    }
    with open("artifact-manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
    print(f"artifact-manifest.json gerado ({len(arquivos)} arquivo(s))")


if __name__ == "__main__":
    main()
