# tools/ensaio-lora

Ferramentas do ensaio de alcance LoRa sobre o mar. Plano completo, lista de
equipamentos e protocolo em `docs/05-ENSAIO-LORA.md`.

| Arquivo | O que é |
|---|---|
| `no_ensaio.ino` | Firmware de referência do nó (T-Beam / SX1262). Transmite alternando SF e **grava tudo localmente no cartão SD**. Adaptar aos pinos da sua placa e compilar antes de ir a campo. |
| `simular_ensaio.py` | Gera dados sintéticos no formato exato do campo. Serve para ensaiar a análise antes do dia de barco e treinar a equipe. **Dados simulados, não medição.** |
| `analisar_ensaio.py` | Análise do ensaio 1: PDR e RSSI por distância e por SF, expoente de perda de percurso, distância de PDR 90%, recalibração do fator do modelo e perda por posição no corpo. |
| `simular_capacidade.py` | Simula N nós contra um gateway com colisão, efeito de captura e limite de demoduladores. Dimensiona o ensaio 2 antes de comprá-lo. **Dados simulados.** |
| `analisar_capacidade.py` | Análise do ensaio 2: carga oferecida, entrega por classe de distância e do pior nó, com intervalo de confiança de Wilson. |

## Ensaio seco, antes de gastar o dia de barco

```bash
python3 simular_ensaio.py --saida-dir /tmp/ensaio

python3 analisar_ensaio.py \
  --gateway /tmp/ensaio/gateway.csv --no /tmp/ensaio/no.csv \
  --gw-lat -2.7961 --gw-lon -40.5137 --gw-altura 30 --bin-km 1.5
```

Com os dados reais, trocar os CSV e as coordenadas do gateway pelos do spot.

## Ensaio de capacidade

```bash
python3 simular_capacidade.py --saida-dir /tmp/cap --duracao-s 1800 --nos 10 20 30 45 60
python3 analisar_capacidade.py --nos /tmp/cap/nos.csv --gateway /tmp/cap/gateway.csv
```

Plano em `docs/06-ENSAIO-CAPACIDADE.md`.

## Quatro armadilhas que o código já trata

**O nó precisa gravar localmente.** Quando o enlace cai, a posição não chega ao
gateway — e é justamente essa a posição que define o limite de alcance. Sem log
no nó, o ensaio mede só até onde o gateway já ouvia.

**O ajuste do expoente só vale onde quase tudo chega.** Além do limiar de
sensibilidade, só passam os pacotes que pegaram desvanecimento favorável, e o
RSSI mediano fica artificialmente alto. A análise ajusta apenas nas faixas com
PDR ≥ 90%; sem isso, o expoente sai subestimado (3,1 em vez de 4,0 no teste).

**A média esconde a falha de capacidade.** Pelo efeito de captura, quem perde a
colisão é sempre o nó mais fraco — o praticante distante, que é justamente por
quem o sistema existe. No simulado, entrega agregada de 91% convivia com 13% na
classe crítica. O índice de Jain ficou em 0,99 durante todo o colapso: justiça
agregada é a métrica errada aqui. A análise reporta por classe e pelo pior nó.

**Rodada curta superestima capacidade.** Uma taxa estimada sobre poucas dezenas
de pacotes é ruído: rodadas de 10 min indicaram 27 praticantes onde rodadas de
30 min entregaram 10. A análise calcula o tamanho de amostra necessário, aplica
intervalo de confiança de Wilson e devolve "indefinido" em vez de aprovar quando
o intervalo cruza o alvo.
