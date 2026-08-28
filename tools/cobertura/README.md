# tools/cobertura

Estimativa de alcance do sinal celular sobre o mar, a partir de cada spot.

| Arquivo | O que é |
|---|---|
| `fisica.py` | Calcula as tabelas de horizonte de rádio, orçamento de enlace e Fresnel. Roda sozinho, sem dados externos. |
| `estimar_cobertura.py` | Pipeline principal. Consome a base de ERBs da ANATEL + a lista de spots e produz CSV e GeoJSON. |
| `spots_brasil.csv` | 51 spots de kite/wing do litoral brasileiro, com coordenada aproximada e perfil de uso. |
| `fixtures/erb_exemplo.csv` | Base falsa de 7 ERBs, só para verificar que o pipeline roda. **Não usar como dado.** |

## Uso

```bash
python3 fisica.py                     # tabelas de física, sem dependências

python3 estimar_cobertura.py \
  --erb Estacoes_Licenciadas_SMP.csv \
  --spots spots_brasil.csv \
  --saida-csv cobertura_spots.csv \
  --saida-geojson cobertura_spots.geojson

python3 estimar_cobertura.py --erb ... --spots ... --corredor CE04,CE01
python3 estimar_cobertura.py --help   # todos os parâmetros do modelo
```

A base de ERBs **não acompanha o repositório**. Baixe o conjunto "Estações
Licenciadas a operar no Serviço Móvel Pessoal" em dados.gov.br e filtre pelos
municípios do litoral antes de processar.

Método, premissas e limitações: `docs/03-COBERTURA-CELULAR-OFFSHORE.md`.
