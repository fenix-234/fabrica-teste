# Ensaio 1 — Alcance LoRa sobre o mar

**O que este ensaio decide:** se o LoRa entra como camada primária do GUARDIAN-KITE ou se a arquitetura volta a ser centrada em celular.
**Duração:** 1 dia de campo, mais 1 dia de bancada antes e 1 de análise depois.
**Data:** 2026-08-28

---

## 1. Objetivo

O levantamento de tecnologias calculou que **o LoRa em SF12, com gateway a 30 m, satura o horizonte de rádio: 26,3 km**, contra 7,9 km do LTE na mesma altura. Toda a arquitetura revisada depende desse número, e ele nunca foi medido no mar brasileiro.

O ensaio produz quatro respostas:

| # | Pergunta | Como se mede |
|---|---|---|
| 1 | Até que distância o rastreio é **confiável**? | Distância em que a taxa de entrega cai abaixo de 90%, por SF |
| 2 | A propagação segue o modelo de dois raios? | Expoente de perda de percurso ajustado — esperado n ≈ 4 |
| 3 | Quanto custa carregar o dispositivo no corpo? | RSSI na mesma distância, em quatro posições |
| 4 | O fator de calibração de 1,5 está certo? | Razão entre o medido e o modelo de dois raios |

A resposta 4 realimenta `tools/cobertura/estimar_cobertura.py` e, com ela, **todo o estudo de cobertura das praias precisa ser refeito** se o desvio for grande.

---

## 2. Hipóteses, com número

Escritas antes do ensaio, para não haver reinterpretação depois:

| Hipótese | Previsão | Derrubada se |
|---|---|---|
| H1 — alcance SF12 | PDR ≥ 90% até **18–26 km** com gateway a 30 m | ficar abaixo de 10 km |
| H2 — propagação | expoente **n entre 3,4 e 4,6** | n < 2,6 ou n > 4,6 |
| H3 — perda por corpo | **10 ± 4 dB** entre "no ar" e "bolsa no braço" | fora de 5–18 dB |
| H4 — vantagem sobre o LTE | alcance SF12 **≥ 2×** o do LTE medido no mesmo spot | menos que 1,5× |

---

## 3. Lista de equipamentos

> Preços estimados para 2026, em reais, sujeitos a câmbio e importação. Servem para dimensionar, não para orçar.

### 3.1 Gateway — o que fica na praia

| Item | Qtd | Especificação | R$ (un.) | R$ |
|---|---|---|---|---|
| Gateway LoRaWAN outdoor | 1 | 8 canais, SX1302, IP67, **AU915**, PoE — Dragino DLOS8N ou RAK7289 | 3.000 | 3.000 |
| Antena omni de fibra | 1 | 915 MHz, 5,8–8 dBi, conector N-fêmea, para mastro | 400 | 400 |
| Cabo coaxial | 10 m | LMR-400 com conectores N montados — **perde ~1,3 dB nos 10 m a 915 MHz** | 300 | 300 |
| Protetor contra surtos | 1 | N-fêmea / N-fêmea, com aterramento | 200 | 200 |
| Mastro telescópico | 1 | 6 a 9 m, com estais, esticadores e base | 700 | 700 |
| Kit de aterramento | 1 | haste, cabo 6 mm², conectores | 120 | 120 |
| Alimentação | 1 | bateria 12 V 7 Ah + inversor, ou injetor PoE se houver rede elétrica | 450 | 450 |
| Roteador 4G | 1 | backhaul do gateway (opcional — sem ele, gravar log localmente) | 350 | 350 |
| Caixa estanque | 1 | para a eletrônica no pé do mastro | 180 | 180 |
| **Subtotal** | | | | **5.700** |

### 3.2 Nós — o que vai na água

| Item | Qtd | Especificação | R$ (un.) | R$ |
|---|---|---|---|---|
| Placa do nó | 3 | LilyGO T-Beam — ESP32 + **SX1262** + GNSS + suporte 18650. O GNSS embarcado é o motivo da escolha | 450 | 1.350 |
| Antena do nó | 3 | 915 MHz, 2–3 dBi, flexível, SMA — igual à que iria no produto | 50 | 150 |
| Bateria 18650 | 6 | 3400 mAh, com carregador — duas por nó, para o dia inteiro | 60 | 400 |
| Cartão microSD | 3 | 32 GB classe 10 — **o log local é obrigatório**, ver seção 7 | 45 | 135 |
| Caixa estanque rígida | 3 | IP67 pequena, com passagem para antena | 130 | 390 |
| Braçadeira e cordinha | 3 | fixação no braço e cabo de segurança | 40 | 120 |
| **Subtotal** | | | | **2.545** |

### 3.3 Medição, apoio e segurança

| Item | Qtd | Para quê | R$ |
|---|---|---|---|
| Barco com condutor | 1 diária | O transecto. Precisa manter 20–25 km/h estáveis | 1.200 |
| Combustível | — | ~60 km de percurso | 300 |
| Coletes salva-vidas | 3 | **Obrigatório** | — |
| Rádio VHF portátil | 1 | Segurança e coordenação praia ↔ barco | 600 |
| Anemômetro portátil | 1 | Registrar vento por transecto — define o estado do mar | 250 |
| Trena a laser | 1 | Medir a altura real da antena. Errar 5 m aqui desloca todo o resultado | 250 |
| Power bank | 1 | Notebook e telefones no barco | 150 |
| Notebook | 1 | Log do gateway e conferência em campo | — |
| Ferramentas e consumíveis | — | abraçadeiras, fita de autofusão, chaves, silicone | 150 |
| **Subtotal** | | | **2.900** |

### 3.4 Total

| Configuração | Custo | Quando serve |
|---|---|---|
| **Kit mínimo de rádio** — gateway indoor em caixa estanque, 2 nós, antena, sem mastro nem barco | **R$ 3.100** | Se já existe ponto alto com energia e um barco emprestado |
| **Ensaio completo** | **R$ 11.145** | O que este plano descreve |

> **Correção do que eu disse antes.** No levantamento de tecnologias estimei "menos de R$ 3 mil" para este ensaio. Isso cobre só o rádio. Com mastro, barco, segurança e instrumentação, o dia custa cerca de **R$ 11 mil**. O gateway e os nós ficam para os ensaios seguintes e para o piloto, então o custo não se repete.

---

## 4. Montagem do gateway

1. Escolher o ponto mais alto disponível com visada limpa do mar: mastro do clube, laje, duna. **Registrar a altura real da antena com trena a laser** e a coordenada com GNSS.
2. Antena no topo, cabo o mais curto possível. Cada metro de LMR-400 custa 0,13 dB a 915 MHz — 20 m de cabo jogam fora 2,6 dB, o equivalente a perder 16% do alcance no modelo de dois raios.
3. Protetor de surto na base da antena, aterrado.
4. Configurar o gateway em **AU915**, sub-banda 2 (canais 8–15), que é a usada no Brasil. Conferir na interface antes de sair do lugar.
5. Teste de referência: nó a 200 m em linha de visada, anotar RSSI. Serve de âncora para detectar cabo mal montado ou antena com defeito — se o RSSI a 200 m estiver mais de 6 dB abaixo do previsto, **parar e investigar antes do transecto**.

---

## 5. Protocolo do dia

### D-7 — bancada
- [ ] Montar os três nós, gravar o firmware, conferir gravação no cartão SD
- [ ] Rodar o ensaio seco: `simular_ensaio.py` seguido de `analisar_ensaio.py`
- [ ] Teste em terra: nó a 1 km do gateway, conferir que o CSV do nó e o do gateway casam por `seq`
- [ ] Conferir plano AU915 nos nós e no gateway
- [ ] Carregar todas as baterias

### D-1 — montagem
- [ ] Instalar mastro, antena, cabo, aterramento
- [ ] Medir e anotar altura da antena e coordenada do gateway
- [ ] Teste de referência a 200 m
- [ ] Deixar o gateway gravando a noite toda — confirma estabilidade e revela interferência local

### D0 — campo

| Hora | Atividade | Observações a registrar |
|---|---|---|
| 07:00 | Briefing de segurança, conferência de coletes e VHF | — |
| 07:30 | Teste de referência repetido; sincronizar relógios de nó e gateway | RSSI a 200 m |
| 08:00 | **Transecto 1** — perpendicular à praia, mar adentro, até perda total de sinal por 10 min contínuos | vento, altura de onda, hora |
| 10:30 | **Ensaio estático** — barco ancorado a 2 km; 40 pacotes em cada posição: no ar no mastro do barco, no braço, no colete, submerso 10 cm | trocar `POSICAO_CORPO` no firmware entre os trechos |
| 11:30 | **Transecto 2** — paralelo à costa a 3 km de distância, 10 km de extensão | mede o corredor, não só o pico |
| 13:00 | **Transecto 3** — perpendicular, segundo azimute, 5 km ao lado do primeiro | confirma que o resultado não é de um único rumo |
| 15:00 | **Transecto 4** — repetição do transecto 1 com o mar mais formado da tarde | a diferença entre 1 e 4 é a medida do sombreamento por onda |
| 16:30 | Desmontagem, conferência dos cartões SD **antes de sair da praia** | — |

### D+1 — análise
- [ ] Rodar `analisar_ensaio.py` com os CSV reais
- [ ] Comparar com as hipóteses da seção 2
- [ ] Se o fator de calibração mudar mais que 0,5, refazer `estimar_cobertura.py` para os 51 spots
- [ ] Escrever o relatório com os quatro números da seção 1

---

## 6. Velocidade e densidade de amostras

O nó transmite a cada 2 s, alternando SF7, SF9, SF10 e SF12 — ou seja, **cada SF é medido a cada 8 s**. A 22 km/h, isso dá uma amostra por SF a cada 49 m. Em faixas de 500 m, são cerca de 10 amostras por SF por faixa: suficiente para uma taxa de entrega com sentido.

**Não passar de 25 km/h.** Acima disso a densidade cai e as faixas do fim do transecto, que são justamente as que definem o limite, ficam com poucas amostras.

---

## 7. As duas armadilhas que arruinariam o ensaio

### 7.1 O nó tem que gravar localmente

Quando o enlace cai, a posição não chega ao gateway. Se o único registro estiver no gateway, o ensaio mede *até onde o gateway ainda ouvia* — que é exatamente a resposta que já se sabia. **A posição que interessa é a de onde o pacote não chegou.** Por isso o firmware grava cada transmissão no cartão SD, e por isso a conferência do cartão entra no roteiro antes de sair da praia.

### 7.2 O ajuste do expoente só vale onde quase tudo chega

Além do limiar de sensibilidade, só passam os pacotes que pegaram desvanecimento favorável. O RSSI mediano dos que chegaram fica artificialmente alto, e a curva parece mais plana do que é. No ensaio seco, ajustar sobre todas as faixas dava **n = 3,1**; ajustando só nas faixas com PDR ≥ 90%, o valor volta para **n = 3,8 a 4,1**, que é o injetado no simulador. A análise já faz isso — está registrado aqui para quem for revisar o método.

---

## 8. Registro de campo

Uma folha por transecto, preenchida à mão e fotografada:

```
Transecto nº ____   Data ____   Início ____  Fim ____
Rumo ____°   Distância máxima atingida ____ km
Vento: direção ____  intensidade ____ kt
Altura de onda estimada ____ m     Maré ____
Embarcação: ____________  Velocidade média ____ km/h
Altura da antena do nó sobre a água ____ m   Posição no corpo: ____________
Gateway: altura ____ m   coordenada ____________
Anotações (falhas, paradas, embarcações próximas, chuva):
```

---

## 9. Critérios de decisão

Aplicados sobre a distância de PDR ≥ 90% em SF12, corrigida para gateway de 30 m:

| Resultado | Leitura | Ação |
|---|---|---|
| **≥ 18 km** | Hipótese confirmada | LoRa vira camada primária. Seguir a arquitetura revisada e especificar o hardware em SX126x |
| **10 a 18 km** | Viável, abaixo do previsto | LoRa continua primário, mas exige mastro mais alto ou duna. Recalcular os 51 spots com o novo fator |
| **5 a 10 km** | Empata com o LTE | A vantagem do LoRa passa a ser custo e independência de operadora, não alcance. Reabrir a decisão de arquitetura |
| **< 5 km** | Hipótese derrubada | **Antes de descartar, investigar**: cabo, conectores, plano de frequência, potência configurada, perda por corpo. Um erro de montagem produz exatamente este resultado |

A última linha é a mais importante. Um resultado ruim tem duas explicações possíveis — a física ou a instalação — e a diferença entre elas é o teste de referência a 200 m da seção 4.

---

## 10. Regulatório e segurança

**Rádio.** O Ato ANATEL nº 14448/2017 rege a radiação restrita nas faixas de 902–907,5 e 915–928 MHz, com pico de até 1 W (30 dBm) para sistemas com 35 ou mais canais de salto. O ensaio usa 20 dBm no nó — bem dentro do limite. Placas de desenvolvimento como T-Beam e Heltec em geral **não têm homologação ANATEL**; para um ensaio experimental de baixa potência isso é aceitável, mas **para o produto a homologação é obrigatória**, e o gateway deve ser de modelo homologado. Configurar AU915: usar EU868 ou US915 é transmitir fora do plano brasileiro.

**Estrutura.** Mastro precisa de autorização do proprietário do terreno, estais adequados e aterramento. Não subir mastro com previsão de raio.

**Mar.** Colete para todos, VHF ligado no canal combinado, ninguém sozinho no barco, plano de retorno com horário. O transecto vai a 30 km da costa — **é uma navegação, não um passeio**. Informar a Capitania se for a praxe local.

---

## 11. Riscos do ensaio

| Risco | Consequência | Prevenção |
|---|---|---|
| Cartão SD falha | Perde o ensaio inteiro | Três nós gravando em paralelo; conferir o log após o primeiro quilômetro |
| GNSS sem fix na partida | Amostras iniciais sem posição | Ligar os nós 10 min antes, confirmar contagem de satélites |
| Plano de frequência errado | Zero pacotes, diagnóstico confuso | Item de conferência em D-7 e D-1 |
| Cabo ou conector mal montado | Resultado ruim atribuído à física | Teste de referência a 200 m |
| Bateria acaba no meio | Transecto truncado | Duas baterias por nó, troca no ensaio estático |
| Barco rápido demais | Poucas amostras no fim do transecto | Limite de 25 km/h combinado com o condutor |
| Mar muito formado | Resultado pessimista sem registro | Anotar vento e onda por transecto; o transecto 4 existe para isolar esse efeito |
| Interferência local | Ruído de fundo alto | Gateway gravando a noite anterior |

---

## 12. Entregáveis

1. CSV bruto do gateway e dos três nós, arquivados sem edição
2. `ensaio_resultado.csv` com as curvas de PDR e RSSI por SF e distância
3. Relatório de uma página com os quatro números da seção 1 e o veredito da seção 9
4. Fator de calibração novo, aplicado em `estimar_cobertura.py`
5. Se o fator mudar, o estudo de cobertura dos 51 spots refeito
6. Fotos da montagem e das folhas de campo

---

## 13. Ferramentas

Em `tools/ensaio-lora/`:

- `no_ensaio.ino` — firmware de referência do nó
- `simular_ensaio.py` — gera dados sintéticos no formato do campo, para o ensaio seco
- `analisar_ensaio.py` — a análise completa

```bash
# ensaio seco, antes de gastar o dia de barco
python3 simular_ensaio.py --saida-dir /tmp/ensaio
python3 analisar_ensaio.py --gateway /tmp/ensaio/gateway.csv --no /tmp/ensaio/no.csv \
  --gw-lat -2.7961 --gw-lon -40.5137 --gw-altura 30 --bin-km 1.5
```
