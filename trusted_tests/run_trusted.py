"""trusted_tests/run_trusted.py — executa os testes de aceitacao CONFIAVEIS que vivem na main
protegida (nao no conteudo modificavel do PR). Verifica o hash de cada teste contra o manifesto
confiavel, roda por pytest e valida ESTRUTURALMENTE o junit (0 fail/err/skip inesperado; >0 testes).
Arquivo CONFIAVEL (main; CODEOWNERS). Jobs da fabrica nao podem altera-lo."""
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ACEITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aceite")
MANIFESTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifesto.json")


def _hashes():
    h = {}
    if os.path.isdir(ACEITE_DIR):
        for n in sorted(os.listdir(ACEITE_DIR)):
            p = os.path.join(ACEITE_DIR, n)
            if os.path.isfile(p) and n.endswith(".py"):
                h[n] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return h


def main():
    if not os.path.isdir(ACEITE_DIR) or not _hashes():
        # sem testes de aceitacao confiaveis definidos p/ este projeto: nao ha o que validar
        print("run_trusted: nenhum teste de aceitacao confiavel definido (ok, no-op)")
        return
    atuais = _hashes()
    # verifica hashes contra o manifesto confiavel, se existir
    if os.path.isfile(MANIFESTO):
        esperado = json.load(open(MANIFESTO, encoding="utf-8")).get("testes", {})
        if set(atuais) != set(esperado) or any(atuais[k] != esperado.get(k) for k in atuais):
            print("TAMPER: testes de aceitacao confiaveis divergem do manifesto")
            sys.exit(2)
    rep = os.path.join(os.getcwd(), "reports", "junit_trusted.xml")
    os.makedirs(os.path.dirname(rep), exist_ok=True)
    rc = subprocess.call([sys.executable, "-I", "-m", "pytest", ACEITE_DIR, "-q",
                          "-p", "no:cacheprovider", "--junitxml", rep])
    if not os.path.isfile(rep):
        print("run_trusted: junit ausente"); sys.exit(1)
    ts = ET.parse(rep).getroot()
    ts = ts if ts.tag == "testsuite" else ts.find("testsuite")
    tests = int(ts.get("tests", "0")); fails = int(ts.get("failures", "0"))
    errs = int(ts.get("errors", "0")); skip = int(ts.get("skipped", "0"))
    ok = (tests > 0 and fails == 0 and errs == 0 and skip == 0)
    print(f"run_trusted: tests={tests} fail={fails} err={errs} skip={skip} rc={rc} -> {'OK' if ok else 'FALHOU'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
