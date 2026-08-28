# tools/ensaio-lora

Ferramentas do ensaio de alcance LoRa sobre o mar. Plano completo, lista de
equipamentos e protocolo em `docs/05-ENSAIO-LORA.md`.

| Arquivo | O que é |
|---|---|
| `no_ensaio.ino` | Firmware de referência do nó (T-Beam / SX1262). Transmite alternando SF e **grava tudo localmente no cartão SD**. Adaptar aos pinos da sua placa e compilar antes de ir a campo. |
| `simular_ensaio.py` | Gera dados sintéticos no formato exato do campo. Serve para ensaiar a análise antes do dia de barco e treinar a equipe. **Dados simulados, não medição.** |
| `analisar_ensaio.py` | Análise: PDR e RSSI por distância e por SF, expoente de perda de percurso, distância de PDR 90%, recalibração do fator do modelo e perda por posição no corpo. |

## Ensaio seco, antes de gastar o dia de barco

```bash
python3 simular_ensaio.py --saida-dir /tmp/ensaio

python3 analisar_ensaio.py \
  --gateway /tmp/ensaio/gateway.csv --no /tmp/ensaio/no.csv \
  --gw-lat -2.7961 --gw-lon -40.5137 --gw-altura 30 --bin-km 1.5
```

Com os dados reais, trocar os CSV e as coordenadas do gateway pelos do spot.

## Duas armadilhas que o código já trata

**O nó precisa gravar localmente.** Quando o enlace cai, a posição não chega ao
gateway — e é justamente essa a posição que define o limite de alcance. Sem log
no nó, o ensaio mede só até onde o gateway já ouvia.

**O ajuste do expoente só vale onde quase tudo chega.** Além do limiar de
sensibilidade, só passam os pacotes que pegaram desvanecimento favorável, e o
RSSI mediano fica artificialmente alto. A análise ajusta apenas nas faixas com
PDR ≥ 90%; sem isso, o expoente sai subestimado (3,1 em vez de 4,0 no teste).
