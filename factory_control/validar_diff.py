"""factory_control/validar_diff.py — roda no CI ANTES de instalar/rodar o projeto do PR.
Recusa: alteracao de arquivos protegidos e dependencias git/url/path/nao-fixadas. Sai !=0 no bloqueio.
Arquivo CONFIAVEL: vem da main protegida (CODEOWNERS); jobs da fabrica nao podem altera-lo."""
import os
import re
import subprocess
import sys

PROTEGIDOS = (".github/workflows/", ".github/codeowners", "factory_control/", "trusted_tests/")


def _arquivos_alterados():
    base = os.environ.get("GITHUB_BASE_REF", "main")
    subprocess.run(["git", "fetch", "--depth=1", "origin", base], capture_output=True)
    r = subprocess.run(["git", "diff", "--name-only", f"origin/{base}...HEAD"],
                       capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def main():
    erros = []
    for f in _arquivos_alterados():
        nl = f.replace("\\", "/").lower()
        if any(nl == p or nl.startswith(p) for p in PROTEGIDOS):
            erros.append(f"arquivo protegido alterado: {f}")
    if os.path.isfile("pyproject.toml"):
        txt = open("pyproject.toml", encoding="utf-8").read()
        if re.search(r"git\+|@\s*git|\bgit\s*=", txt):
            erros.append("dependencia git em pyproject.toml")
        if re.search(r"\bpath\s*=\s*[\"']", txt):
            erros.append("dependencia path local em pyproject.toml")
        if re.search(r"(url)\s*=\s*[\"']https?://", txt):
            erros.append("dependencia url em pyproject.toml")
    if not os.path.isfile("uv.lock"):
        erros.append("uv.lock ausente (dependencias nao travadas)")
    if erros:
        print("POLICY_VIOLATION:")
        for e in erros:
            print(" -", e)
        sys.exit(1)
    print("politica do diff OK")


if __name__ == "__main__":
    main()
