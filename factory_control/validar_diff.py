"""factory_control/validar_diff.py — politica do diff. FALHA FECHADO (fail-closed).
Recusa: alteracao de arquivos protegidos e dependencias git/url/path/nao-fixadas
(inspeciona pyproject.toml E uv.lock). Sai !=0 em qualquer bloqueio E em qualquer
erro de git — na duvida, BLOQUEIA.

Veredito AUTORITATIVO: este script deve ser executado a partir da main confiavel
(estagio factory-verify via workflow_run), nunca da copia do PR. Aceita as refs
base/head por variavel de ambiente para funcionar nesse estagio:
  FABRICA_BASE_REF (default: GITHUB_BASE_REF ou 'main')
  FABRICA_HEAD_REF (default: GITHUB_SHA ou 'HEAD')
Arquivo CONFIAVEL (main; CODEOWNERS). Jobs da fabrica nao podem altera-lo."""
import os
import re
import subprocess
import sys

PROTEGIDOS = (".github/workflows/", ".github/codeowners", "factory_control/", "trusted_tests/")
ARQS_DEP = ("pyproject.toml", "uv.lock")


def _sh(args, obrigatorio=True):
    """Executa git; se obrigatorio e falhar, ABORTA bloqueando (fail-closed)."""
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0 and obrigatorio:
        print(f"ERRO_GIT (bloqueando por seguranca): {' '.join(args)}", file=sys.stderr)
        print((r.stderr or "").strip(), file=sys.stderr)
        sys.exit(3)
    return r.stdout


def _arquivos_alterados():
    base = os.environ.get("FABRICA_BASE_REF") or os.environ.get("GITHUB_BASE_REF") or "main"
    head = os.environ.get("FABRICA_HEAD_REF") or os.environ.get("GITHUB_SHA") or "HEAD"
    # Historico suficiente: NAO usar --depth=1 (quebra o merge-base e mascara mudancas).
    _sh(["git", "fetch", "--no-tags", "origin", base])
    if head != "HEAD":
        _sh(["git", "fetch", "--no-tags", "origin", head], obrigatorio=False)
    mb = _sh(["git", "merge-base", f"origin/{base}", head]).strip()
    if not mb:
        print("ERRO: merge-base vazio (bloqueando por seguranca)", file=sys.stderr)
        sys.exit(3)
    out = _sh(["git", "diff", "--name-only", f"{mb}..{head}"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def _checar_dependencias(erros):
    for nome in ARQS_DEP:
        if not os.path.isfile(nome):
            continue
        low = open(nome, encoding="utf-8", errors="replace").read().lower()  # case-insensitive
        if re.search(r"git\+|@\s*git|\bgit\s*=", low):
            erros.append(f"dependencia git em {nome}")
        if re.search(r"\bpath\s*=\s*[\"']", low):
            erros.append(f"dependencia path local em {nome}")
        if re.search(r"\burl\s*=\s*[\"']https?://", low):
            erros.append(f"dependencia url em {nome}")
    if os.path.isfile("pyproject.toml") and not os.path.isfile("uv.lock"):
        erros.append("uv.lock ausente (dependencias nao travadas)")


def main():
    erros = []
    for f in _arquivos_alterados():
        nl = f.replace("\\", "/").lower()
        if any(nl == p or nl.startswith(p) for p in PROTEGIDOS):
            erros.append(f"arquivo protegido alterado: {f}")
    _checar_dependencias(erros)
    if erros:
        print("POLICY_VIOLATION:")
        for e in erros:
            print(" -", e)
        sys.exit(1)
    print("politica do diff OK")


if __name__ == "__main__":
    main()
