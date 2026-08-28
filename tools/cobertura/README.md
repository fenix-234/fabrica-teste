# tools/cobertura

Estimativa de alcance do sinal celular sobre o mar, a partir de cada spot.

| Arquivo | O que é |
|---|---|
| `fisica.py` | Calcula as tabelas de horizonte de rádio, orçamento de enlace e Fresnel. Roda sozinho, sem dados externos. |
| `comparar_tecnologias.py` | Compara LTE, LoRa, AIS-MOB, HaLow e satélite no mesmo modelo: alcance, capacidade, custo por sessão e malha entre praticantes. Roda sozinho. |
| `estimar_cobertura.py` | Pipeline principal. Consome a base de ERBs da ANATEL + a lista de spots e produz CSV e GeoJSON. |
| `spots_brasil.csv` | 51 spots de kite/wing do litoral brasileiro, com coordenada aproximada e perfil de uso. |
| `fixtures/erb_exemplo.csv` | Base falsa de 7 ERBs, só para verificar que o pipeline roda. **Não usar como dado.** |
| `tests/test_fisica.py` | 40 asserções sobre física, geometria, parser e classificação. |
| `tests/gerar_base_sintetica.py` | Gera arquivo no formato da ANATEL para teste de carga. **Dados inventados.** |

## Testes

```bash
python3 tests/test_fisica.py                       # 40 asserções, ~1 s

# teste de carga: 3 milhões de linhas, ~33 s, pico de 423 MB
python3 tests/gerar_base_sintetica.py spots_brasil.csv /tmp/sintetico.csv 3000000
python3 estimar_cobertura.py --erb /tmp/sintetico.csv --spots spots_brasil.csv
```

## Uso

```bash
python3 fisica.py                     # tabelas de física, sem dependências
python3 comparar_tecnologias.py       # comparação entre tecnologias de enlace

python3 estimar_cobertura.py \
  --erb Estacoes_Licenciadas_SMP.csv \
  --spots spots_brasil.csv \
  --saida-csv cobertura_spots.csv \
  --saida-geojson cobertura_spots.geojson

python3 estimar_cobertura.py --erb ... --spots ... --corredor CE04,CE01
python3 estimar_cobertura.py --erb base.csv.gz --spots ... --uf CE,PI,MA
python3 estimar_cobertura.py --help   # todos os parâmetros do modelo
```

Aceita `.csv`, `.csv.gz` e `.zip`. Detecta delimitador e encoding, lê coordenada
decimal ou em grau-minuto-segundo, calcula o EIRP a partir de potência e ganho
quando a base informa, e considera o apontamento das antenas. A leitura é em
streaming com filtro por célula, então a memória acompanha o número de estações
úteis, não o tamanho do arquivo.
```

A base de ERBs **não acompanha o repositório**. Baixe o conjunto "Estações
Licenciadas a operar no Serviço Móvel Pessoal" em dados.gov.br e filtre pelos
municípios do litoral antes de processar.

Método, premissas e limitações: `docs/03-COBERTURA-CELULAR-OFFSHORE.md`.
