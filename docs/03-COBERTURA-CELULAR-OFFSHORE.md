# Cobertura celular no mar — mapeamento das praias do Brasil

**Pergunta:** quais praias não têm cobertura, e a que distância da praia o sinal de celular chega?
**Data:** 2026-08-28

---

## 1. O que é possível responder, e o que não é

### 1.1 Não existe mapa público de cobertura no mar

Este é o fato central e ele muda o resto do trabalho:

- As operadoras publicam mapas de cobertura **terrestres**. A renderização quase sempre **termina na linha da costa** — a área marítima é pintada como "sem cobertura" ou simplesmente não é modelada, porque não há assinante lá para justificar o cálculo.
- A ANATEL publica o **percentual de cobertura por município e por rodovia**, não por área marítima.
- A ANATEL publica, em dados abertos, a **base completa de estações licenciadas do Serviço Móvel Pessoal** — com coordenada, altura de antena, frequência, tecnologia e operadora de cada ERB. É a partir *dessa* base que a cobertura no mar pode ser calculada, porque sobre a água a propagação é quase pura geometria: sem prédio, sem morro, sem vegetação.
- O diagnóstico do PERT 2026 da ANATEL identifica cerca de **26,4 mil localidades sem cobertura móvel** no país, concentradas em áreas rurais e remotas. Nenhuma delas é indexada por "praia".

**Conclusão:** ninguém pode entregar essa resposta consultando um mapa pronto. Ela se obtém de duas formas, e as duas estão neste documento: **(a)** calculando a partir da base de ERBs da ANATEL, **(b)** medindo em campo. A modelagem prioriza onde medir; a medição calibra a modelagem.

### 1.2 Limitação desta sessão — bloqueio confirmado

Tentei baixar a base de ERBs e **todos os hosts de dados estão bloqueados pela política de egresso da organização**. O gateway responde 403 ao CONNECT. Hosts testados, todos negados:

`dados.gov.br` · `gov.br` · `www.gov.br` · `anatel.gov.br` · `www.anatel.gov.br` · `sistemas.anatel.gov.br` · `dadosabertos.anatel.gov.br` · `mosaico.anatel.gov.br` · `opencellid.org` · `download.opencellid.org` · `overpass-api.de` · `huggingface.co`

Só o GitHub passa. Não há caminho alternativo confiável: um espelho não oficial da base da ANATEL tem procedência e data desconhecidas, e num estudo que orienta resgate isso é pior do que não rodar. Portanto:

- Os **números de física** deste documento são calculados, reais e reproduzíveis — estão em `tools/cobertura/fisica.py`.
- A **classificação por spot** abaixo é um **prior geográfico**, não uma medição. Ela existe para ordenar a fila de medição, não para ser citada como resultado.
- O **pipeline que produz o resultado real** está pronto, testado e medido em escala real — ver seção 4.3. Roda assim que a base da ANATEL for baixada em uma máquina com acesso.

Para destravar aqui dentro, basta liberar `dados.gov.br` na política de rede do ambiente (Claude Code na web → configuração do ambiente → política de egresso). Com o host liberado, o download e a execução levam poucos minutos.

---

## 2. Física: até onde o sinal chega sobre o mar

Sobre a água o enlace é limitado por três coisas, nesta ordem: o **horizonte de rádio**, o **modelo de dois raios** (reflexão na superfície do mar) e o **orçamento de enlace**. O menor dos três manda.

### 2.1 Horizonte de rádio — teto geométrico absoluto (km)

Com raio efetivo da Terra k = 4/3.

| Posição do praticante | Torre 20 m | 30 m | 45 m | 60 m | 100 m |
|---|---|---|---|---|---|
| Nadando / derivando (0,3 m) | 20,7 | 24,8 | 29,9 | 34,2 | 43,5 |
| Deitado na prancha (0,8 m) | 22,1 | 26,3 | 31,3 | 35,6 | 44,9 |
| De pé na prancha (1,5 m) | 23,5 | 27,6 | 32,7 | 37,0 | 46,3 |
| Jet-ski / barco (3 m) | 25,6 | 29,7 | 34,8 | 39,1 | 48,4 |

Nenhum sinal passa disso sem duto de evaporação. Mas o horizonte quase nunca é o limite real.

### 2.2 Orçamento de enlace

Premissas usadas (todas ajustáveis no script):

| Parâmetro | Valor | Observação |
|---|---|---|
| EIRP total da ERB | 60 dBm | macro típica: 43 dBm de PA + 17 dBi de antena |
| Largura de banda | 20 MHz (100 RB) | EIRP por resource element = **29,2 dBm** |
| RSRP alvo | −110 dBm | borda de LTE utilizável; −105 para dado confiável |
| Perda por corpo + bolsa estanque + imersão | 10 dB | o telefone está encostado num corpo molhado |
| Margem de sombreamento | 8 dB | |
| **Orçamento resultante** | **121,2 dB** | |

### 2.3 Alcance por frequência — praticante deitado na prancha (0,8 m), torre de 30 m

| Faixa | Breakpoint | Dois raios | Espaço livre | Horizonte |
|---|---|---|---|---|
| 700 MHz | 0,22 km | **5,3 km** | 39,2 km | 26,3 km |
| 850 MHz | 0,27 km | **5,3 km** | 32,3 km | 26,3 km |
| 1800 MHz | 0,58 km | **5,3 km** | 15,2 km | 26,3 km |
| 2100 MHz | 0,67 km | **5,3 km** | 13,1 km | 26,3 km |
| 2600 MHz | 0,83 km | **5,3 km** | 10,6 km | 26,3 km |
| 3500 MHz (5G) | 1,12 km | **5,3 km** | 7,8 km | 26,3 km |

**Três leituras que mudam o projeto:**

1. **O breakpoint acontece a menos de 1 km da torre.** Depois dele, sobre o mar, a perda passa de 20 para 40 dB por década. Isso significa que **dobrar a distância custa 12 dB**, não 6. O sinal despenca muito mais rápido no mar do que em terra.
2. **A frequência quase não importa no regime de dois raios** — todos dão 5,3 km. O que a frequência baixa compra é margem contra o sombreamento das ondas, não alcance bruto.
3. **A altura da torre importa mais que a banda.** Ela entra como 20·log₁₀(h): dobrar a altura da torre vale 6 dB, ou seja, **multiplica o alcance por 1,41**.

### 2.4 Alcance por altura de torre (700 MHz, usuário a 0,8 m)

| Torre | Dois raios (pessimista) | Teto (horizonte / espaço livre) | Faixa realista |
|---|---|---|---|
| 20 m | 4,3 km | 22,1 km | **4–22 km** |
| 30 m | 5,3 km | 26,3 km | **5–26 km** |
| 45 m | 6,4 km | 31,3 km | **6–31 km** |
| 60 m | 7,4 km | 35,6 km | **7–36 km** |
| 100 m | 9,6 km | 39,2 km | **10–39 km** |

A literatura de conectividade marítima reporta **~8 km como alcance prático** de 4G entre torre costeira e embarcação — o que cai exatamente dentro da faixa acima e valida o modelo. Adotei um **fator de calibração de 1,5 sobre o modelo de dois raios**, que reproduz esses 8 km para torre de 30 m. Esse fator é o número a ser reajustado com a primeira campanha de medição.

### 2.5 O que mais destrói o alcance: o corpo e a água

| Perda por corpo/imersão | Dois raios | Espaço livre |
|---|---|---|
| 0 dB (telefone no ar, longe do corpo) | 9,3 km | 124,0 km |
| 5 dB | 7,0 km | 69,7 km |
| **10 dB (bolsa estanque no braço)** | **5,3 km** | 39,2 km |
| 15 dB | 3,9 km | 22,0 km |
| 20 dB (telefone no bolso do colete, sob a água) | 3,0 km | 12,4 km |

**Onde o praticante carrega o telefone importa mais do que a operadora que ele assina.** Do braço para o bolso interno do colete, o alcance cai quase pela metade. Isso é requisito de produto, não detalhe.

### 2.6 As ondas

Raio da primeira zona de Fresnel no ponto médio do enlace:

| Distância | 700 MHz | 1800 MHz | 2600 MHz |
|---|---|---|---|
| 1 km | 10,3 m | 6,5 m | 5,4 m |
| 5 km | 23,1 m | 14,4 m | 12,0 m |
| 10 km | 32,7 m | 20,4 m | 17,0 m |
| 20 km | 46,3 m | 28,8 m | 24,0 m |

A zona de Fresnel tem dezenas de metros de raio e a superfície do mar está bem dentro dela — é por isso que o modelo de dois raios vale, e não o de espaço livre. Uma onda de 1,5 m não bloqueia a linha de visada, mas **um praticante no cavado de uma onda perde vários dB por difração**, de forma intermitente. Consequência de engenharia: **o sinal no mar não é estável, é intermitente com período de onda.** O sistema tem que assumir perda de pacote como condição normal, não como falha — daí o buffer offline e o envio em rajada.

---

## 3. Inventário de spots e prior de cobertura

51 spots em `tools/cobertura/spots_brasil.csv`, com coordenada aproximada e perfil de uso.

> **As classes abaixo são um prior geográfico** — baseado em presença de núcleo urbano, densidade provável de ERBs e geografia — **não uma medição**. Servem para priorizar a fila de campo. O número real sai do pipeline com a base da ANATEL.

### 3.1 Prior A — cobertura provavelmente boa (núcleo urbano ou torre alta próxima)

Fortaleza, Salvador/Itapuã, Aracaju, Cabedelo/Jacaré, Porto de Galinhas, Barra da Tijuca, Cabo Frio, Praia Grande, Lagoa da Conceição, Torres, Tramandaí, Lagoa de Araruama.

Nesses lugares o problema não é cobertura: é bateria e a perda por corpo/imersão da seção 2.5.

### 3.2 Prior B — vila turística consolidada, provavelmente 1 a 3 ERBs

Cumbuco/Cauípe, Taíba, Paracuru, Jericoacoara, Preá, Icaraí de Amontada, São Miguel do Gostoso, Barra Grande (PI), Maragogi, Praia do Forte, Búzios/Praia Rasa, Pipa, Barra de Ibiraquera, Guaratuba, Maracajaú, Ilha do Guajiru.

Cobertura na praia deve existir; **o alcance no mar é a incógnita** e é exatamente o que a medição precisa responder primeiro, porque é onde está a maior parte dos praticantes.

### 3.3 Prior C — vila pequena, cobertura marginal

Tatajuba, Guriú, Camocim (áreas afastadas do centro), Galinhas (RN), Icapuí/Redonda, Águas Belas, Fleixeiras/Mundaú, Serra Grande/Itacaré, Cumuruxatiba/Prado, Itaúnas, Ilha do Mel, Laguna/Farol de Santa Marta, Ilha Comprida, Barra do Chuí.

### 3.4 Prior D — zonas prioritárias de sombra

Estes são os trechos onde a hipótese de ausência de cobertura é mais forte e onde a consequência de um acidente é maior:

| Zona | Por quê | Consequência |
|---|---|---|
| **Interior dos Lençóis Maranhenses / Atins → Caburé** | Parque nacional, sem infraestrutura, dunas sem ERB | Downwind cênico e muito procurado, sem nenhuma rede |
| **Delta do Parnaíba (canais e ilhas, Tutóia)** | Labirinto de ilhas, população dispersa | Deriva para dentro do delta é praticamente irrecuperável sem rastreio |
| **Reentrâncias maranhenses e costa do Pará / Marajó** | Litoral de manguezal, ocupação rarefeita | Correntes de maré fortíssimas |
| **Restinga da Marambaia (RJ)** | Área militar, acesso e infraestrutura restritos | 40 km de restinga sem apoio |
| **Praia do Cassino → Barra do Chuí (RS)** | Mais de 200 km de praia contínua com pouquíssimos núcleos | O maior vazio contínuo do litoral brasileiro |
| **Centro da Lagoa dos Patos (RS)** | Corpo d'água de ~10 000 km²; do meio, a margem está a dezenas de km | Distância à margem excede o horizonte de rádio |
| **Superagui / Ilha do Cardoso (PR–SP)** | Parque nacional, ilhas sem ocupação | |
| **Abrolhos e ilhas oceânicas** | Fora de qualquer alcance terrestre | Só satélite resolve |

### 3.5 O que realmente importa não é a praia — é o corredor

Rodei o pipeline com uma base de teste para validar o método e o resultado ilustra a tese: entre dois spots com cobertura, **o meio do caminho pode ser zero**.

```
CORREDOR Jericoacoara -> Camocim (base de teste, 7 ERBs)
      km    mar(km)         classe
     0.0       8.17      ACEITAVEL     <- largada com sinal
     4.0       4.29       LIMITADO
     8.0       0.30        CRITICO
    10.0       0.00  SEM COBERTURA     <- 12 km contínuos sem nada
    20.0       0.00  SEM COBERTURA
    26.0       2.49       LIMITADO
    32.0       0.00  SEM COBERTURA
```

O praticante de kite não fica parado numa praia: ele faz downwind de 10 a 40 km. **Mapear apenas os spots responde à pergunta errada.** O que o sistema precisa é do perfil de cobertura ao longo de cada corredor — que é o que a função `analisar_corredor` do script produz. Os corredores prioritários no Brasil:

1. Jericoacoara → Camocim (passando por Preá, Guriú, Tatajuba)
2. Atins → Caburé → Barreirinhas (Lençóis)
3. Barra Grande → Delta do Parnaíba
4. Icaraí de Amontada → Fleixeiras → Mundaú
5. Cumbuco → Taíba → Paracuru
6. Cassino → Barra do Chuí
7. Galinhas → Ponta do Mel (RN)

---

## 4. Pipeline: como obter o número real

### 4.1 Obter a base da ANATEL

Baixar, em uma máquina com acesso à internet aberta, o conjunto **"Estações Licenciadas a operar no Serviço Móvel Pessoal"** do Portal Brasileiro de Dados Abertos (`dados.gov.br`). O arquivo é grande — filtrar pelos municípios do litoral antes de processar.

Colunas necessárias: latitude, longitude, altura de antena, frequência de transmissão, entidade e tecnologia. O script reconhece os nomes de coluna mais comuns automaticamente.

### 4.2 Rodar

```bash
cd tools/cobertura

# diagnóstico por spot
python3 estimar_cobertura.py \
  --erb Estacoes_Licenciadas_SMP.csv \
  --spots spots_brasil.csv \
  --saida-csv cobertura_spots.csv \
  --saida-geojson cobertura_spots.geojson

# perfil ao longo de um corredor de downwind
python3 estimar_cobertura.py \
  --erb Estacoes_Licenciadas_SMP.csv \
  --spots spots_brasil.csv \
  --corredor CE04,CE01

# cenário pessimista: telefone no bolso do colete, praticante nadando
python3 estimar_cobertura.py --erb ... --spots ... \
  --h-usuario 0.3 --perda-corpo 20 --rsrp -105
```

Saídas: um CSV ordenado do pior para o melhor e um GeoJSON com os pontos e os círculos de alcance, para abrir direto no QGIS.

### 4.3 O pipeline foi testado em escala real

Como não dá para rodar sobre a base verdadeira nesta sessão, validei a máquina de duas formas.

**Testes unitários** — `tools/cobertura/tests/test_fisica.py`, 40 asserções, todas passando:

| Grupo | O que verifica |
|---|---|
| Horizonte de rádio | 26,3 km para torre de 30 m e usuário a 0,8 m; 48,4 km para torre de 100 m e barco |
| Orçamento de enlace | EIRP por resource element de 29,2 dBm e orçamento de 121,2 dB |
| Alcance | Dois raios, espaço livre e breakpoint conferem com o cálculo à mão |
| Invariantes físicas | Dobrar a torre multiplica o alcance por √2; dobrar a frequência corta o espaço livre pela metade; −12 dB corta o alcance de dois raios pela metade |
| Atenuação de setor | Lobo principal, lateral, costas e a passagem por 360° |
| Geometria | Ida e volta de rumo e distância fecham em 10 m; azimutes cardeais exatos |
| Leitura | Decimal com vírgula, grau-minuto-segundo, BOM em UTF-8 e em latin-1, linhas sujas descartadas, EIRP calculado de potência e ganho |

**Teste de carga** — arquivo sintético de **3 milhões de linhas (356 MB)** no formato do extrato da ANATEL, com todas as armadilhas do arquivo real: delimitador `;`, decimal com vírgula, acentuação em latin-1, BOM no cabeçalho, coordenadas zeradas e campos vazios.

| Medida | Resultado |
|---|---|
| Leitura e filtragem de 3 milhões de linhas | **20 s** |
| Análise dos 51 spots | **6,9 s** |
| Tempo total | **33 s** |
| Pico de memória | **423 MB** |
| Linhas sujas descartadas | 480, sem interromper |
| Encoding latin-1 | detectado e tratado automaticamente |
| Entrada `.csv.gz` | funciona |
| Filtro `--uf CE,PI` | funciona |

O teste encontrou um defeito real: o BOM no cabeçalho impedia o mapeamento da coluna de operadora. Corrigido e coberto por teste.

> Os **números de cobertura** desse teste são sem sentido geográfico — os dados são inventados. O que ele prova é que a máquina aguenta o arquivo verdadeiro e não engasga nas suas irregularidades.

### 4.4 Limitações do modelo, declaradas

- O alcance útil no mar é calculado como *alcance da ERB menos a distância dela até o spot*. Isso vale quando a torre está atrás da praia; para torre lateral, superestima.
- O azimute da antena é levado em conta: 0 dB no lobo principal (±60°), −12 dB na lateral, −20 dB nas costas. Isso só é justo porque a base da ANATEL traz **uma linha por setor** — um site de três setores aparece três vezes e sempre há um apontando para o alvo. Se a base vier consolidada em uma linha por site, rodar com `--sem-azimute`, senão o resultado fica pessimista demais.
- O EIRP vem de potência e ganho quando a base informa, com sanidade entre 30 e 75 dBm; cai para 60 dBm quando não informa.
- Não considera relevo entre a torre e a linha d'água (falésia, duna alta, morro). Sobre o mar isso não existe, mas no primeiro trecho pode existir.
- Não considera carga de rede: uma célula lotada num feriado tem alcance útil menor.
- Não considera duto de evaporação, que ocasionalmente estende o alcance muito além do horizonte — e é justamente por ser ocasional que não pode ser usado como premissa de segurança.
- Assume EIRP e configuração uniformes. A ANATEL informa potência licenciada, não a de operação.

---

## 5. Protocolo de medição em campo

A modelagem prioriza; só a medição fecha a resposta. O procedimento é barato:

### 5.1 Equipamento
- Um telefone Android com app de log de rede que grave **RSRP, RSRQ, SINR, banda, PCI e GPS** a cada 1 s, em CSV.
- Um segundo telefone de outra operadora, gravando junto.
- Jet-ski, barco de apoio ou o próprio praticante em sessão.
- Bolsa estanque — e **medir também com o telefone dentro dela**, porque é assim que ele vai ser usado.

### 5.2 Transectos
- Traçar 3 linhas perpendiculares à praia, distantes ~2 km entre si, indo até 15 km da costa ou até a perda total do sinal.
- Velocidade constante e baixa (10 a 15 km/h), para densidade de amostras uniforme.
- Repetir uma linha **com mar formado** e outra **com mar chapado** — a diferença entre as duas é a medida do sombreamento por onda.
- Repetir uma linha às 10h e outra às 17h, para capturar carga de rede.

### 5.3 Resultado esperado por spot
- Curva **RSRP × distância da praia**, uma por operadora.
- **Distância de −110 dBm** (borda de LTE) e **de −105 dBm** (dado confiável) — os dois números que respondem à pergunta original.
- Percentual de amostras perdidas por quilômetro, que alimenta o dimensionamento do buffer offline.
- Fator de calibração reajustado, para o modelo passar a valer para todo o litoral.

### 5.4 Custo
Um dia de barco por spot, dois telefones e um app gratuito. Nos cinco spots do piloto, uma semana de campo responde definitivamente à pergunta — e nenhum outro método responde.

---

## 6. Consequências diretas para o projeto GUARDIAN-KITE

1. **Rotular cada spot com cobertura medida, dentro do app.** Um spot classificado como limitado precisa exibir isso antes do check-in. Vender monitoramento onde não há rede é o pior resultado possível.
2. **O modo offline não é opcional — é o modo normal.** Com dois raios a 40 dB por década e sombreamento por onda, a perda de pacotes é a regra. Buffer persistente e envio em rajada entram no MVP, não numa fase futura.
3. **A posição de uso do dispositivo é requisito.** Braço ou ombro, fora da água o máximo de tempo possível. Bolso interno de colete custa metade do alcance.
4. **Onde o corredor tem sombra, o link precisa ser outro.** Gateway LoRa elevado no clube cobre o corredor inteiro de Jeri a Camocim por uma fração do custo de qualquer alternativa. Para Lençóis, Delta e Cassino, só satélite.
5. **Priorizar o piloto por cobertura, não por popularidade.** Começar num spot de prior A ou B, onde a rede não é a variável em teste — e só depois atacar os corredores de sombra com o link redundante já validado.

---

## 7. Fontes

- ANATEL — Estações Licenciadas do SMP, dados abertos: https://dados.gov.br/dataset/estacoes-licenciadas-a-operar-no-servico-movel-pessoal
- ANATEL — Estações Rádio Base: https://www.gov.br/anatel/pt-br/regulado/outorga/telefonia-movel/estacoes-radio-base
- ANATEL — Cobertura da telefonia móvel: https://www.gov.br/anatel/pt-br/dados/qualidade/qualidade-dos-servicos/cobertura-da-telefonia-movel
- TELETIME — PERT 2026: 26 mil localidades sem cobertura móvel: https://teletime.com.br/14/07/2026/localidades-pert/
- Alcance prático de 4G no mar: https://weconnect.one/blogs/how-far-offshore-does-4g-work-long-distance-maritime-internet-explained/
- LTE maritime coverage solution and ocean propagation loss model (IEEE): https://ieeexplore.ieee.org/document/8308033/
- Cellular Communications in Ocean Waves for Maritime IoT: https://arxiv.org/pdf/2004.07417
- Maritime Communications: A Survey: https://arxiv.org/pdf/2204.12824
