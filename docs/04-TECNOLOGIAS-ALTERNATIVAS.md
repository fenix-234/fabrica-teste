# Segundo levantamento — outras tecnologias para o monitoramento em tempo real

**Pergunta:** se não for celular, o que mais rastreia um praticante no mar, em tempo real?
**Data:** 2026-08-28
**Base de cálculo:** o mesmo modelo de dois raios e horizonte de rádio validado em `tools/cobertura/tests/test_fisica.py`, aplicado a cada tecnologia com seus próprios parâmetros. Reproduzível: `python3 tools/cobertura/comparar_tecnologias.py`.

---

## 1. Por que refazer o levantamento

O estudo de cobertura celular terminou com uma constatação incômoda: **o alcance prático do 4G a partir da praia é de 5 a 8 km**, e o que limita não é a geometria — é o orçamento de enlace. O horizonte de rádio de uma torre de 30 m é 26 km, mas o LTE só entrega 8 deles.

Isso levanta a pergunta certa: existe alguma tecnologia que **use o horizonte inteiro**? A resposta é sim, e a diferença é grande o bastante para mudar a arquitetura do projeto.

---

## 2. As candidatas

| # | Tecnologia | Já em operação onde | Papel possível |
|---|---|---|---|
| 1 | **LoRa / LoRaWAN com gateway próprio** | Redes marítimas de pesca; rede dos Açores cobre >130 km a partir de gateway em ponto alto de ilha; recorde mundial de 1300 km sobre o mar | Enlace primário de praia |
| 2 | **Satélite IoT clássico** (Iridium SBD, Globalstar) | inReach, ZOLEO, SPOT | Emergência, não rastreio contínuo |
| 3 | **NB-IoT NTN** (3GPP Rel-17): Skylo, Sateliot, Kinéis, Myriota | Comercial desde 2025-26; Kinéis herda o Argos, que rastreia boias e fauna desde os anos 1970 | Corredores sem cobertura terrestre |
| 4 | **Direct-to-Device** (Starlink DTC, AST) | ANATEL destinou as faixas em 2 de julho de 2026; operação comercial não esperada antes de 2027 | Futuro — projetar para, não depender de |
| 5 | **AIS-MOB + estação costeira própria** | Balizas MOB1 já existem; a novidade é a estação receptora na praia | Camada independente de resgate |
| 6 | **Malha rádio entre praticantes** (LoRa mesh, Meshtastic) | Meshtastic em comunidades outdoor | Complemento em pelotão |
| 7 | **Wi-Fi HaLow (802.11ah)** | IoT industrial sub-GHz | Descartado — ver cálculo |
| 8 | **Visão computacional de praia / drone** | FDNY resgata banhistas com drone em Rockaway desde 2026; Auxdron na Espanha; datasets UAV com nadadores, jet-skis e boias anotados | Detecta quem não carrega nada |

---

## 3. O cálculo — alcance sobre o mar

Praticante a 0,8 m da água, perda de corpo e imersão de 10 dB, margem de 10 dB.

| Tecnologia / cenário | Orçamento | Dois raios | **Prático** | Teto | O que limita |
|---|---|---|---|---|---|
| LTE 700 MHz, torre 30 m | 121,2 dB | 5,3 km | **7,9 km** | 26,3 km | orçamento |
| LTE 700 MHz, torre 60 m | 121,2 dB | 7,4 km | **11,1 km** | 35,6 km | orçamento |
| LTE 700 MHz, torre 100 m | 121,2 dB | 9,6 km | **14,4 km** | 39,2 km | orçamento |
| LoRa SF7, gateway 30 m | 129,0 dB | 8,2 km | **12,3 km** | 26,3 km | orçamento |
| LoRa SF10, gateway 30 m | 137,0 dB | 13,0 km | **19,6 km** | 26,3 km | orçamento |
| **LoRa SF12, gateway 30 m** | **143,0 dB** | 18,4 km | **26,3 km** | 26,3 km | **horizonte** |
| **LoRa SF12, gateway 60 m** | 143,0 dB | 26,0 km | **35,6 km** | 35,6 km | **horizonte** |
| **LoRa SF12, duna ou morro 100 m** | 143,0 dB | 33,6 km | **44,9 km** | 44,9 km | **horizonte** |
| **LoRa SF12, drone cativo 120 m** | 143,0 dB | 36,8 km | **48,8 km** | 48,8 km | **horizonte** |
| LoRa SF12, balão cativo 300 m | 143,0 dB | 58,2 km | **75,1 km** | 75,1 km | horizonte |
| LTE 700 MHz, drone cativo 120 m | 121,2 dB | 10,5 km | **15,8 km** | 39,2 km | orçamento |
| AIS-MOB → estação de 30 m | 126,0 dB | 6,9 km | **10,4 km** | 26,3 km | orçamento |
| Wi-Fi HaLow, AP de 30 m | 105,0 dB | 2,1 km | **3,1 km** | 4,6 km | orçamento |

### 3.1 O achado

**Com um gateway a apenas 30 m, o LoRa em SF12 satura o horizonte de rádio.** Ele não fica sem sinal antes de a Terra virar — 26,3 km, contra 7,9 km do LTE na mesma torre. São **3,3 vezes mais alcance**, com um rádio de poucos dólares e sem mensalidade.

E a razão é estrutural: o LTE reparte 60 dBm de EIRP entre 1200 subportadoras, sobrando 29 dBm por resource element, e exige SNR positivo. O LoRa concentra tudo em uma portadora estreita e demodula a **20 dB abaixo do ruído**. São 22 dB de diferença no orçamento — e sobre o mar, onde a perda é de 40 dB por década, 22 dB valem 3,5× de distância.

### 3.2 Corolário: elevar o gateway só ajuda quem tem orçamento sobrando

Repare no contraste das duas últimas linhas relevantes: subir o LoRa de 30 para 120 m leva o alcance de 26 para **48,8 km**. Subir o LTE para os mesmos 120 m leva de 7,9 para apenas **15,8 km** — porque ele continua limitado pelo orçamento, não pelo horizonte. **Altura só compra alcance para quem já está encostado no horizonte.** Um drone cativo com gateway LTE é dinheiro jogado fora; com gateway LoRa, cobre um corredor inteiro de downwind.

### 3.3 Validação independente do modelo

O modelo prevê **10,4 km** para uma baliza AIS-MOB até uma estação costeira de 30 m. O valor publicado pelos fabricantes para AIS-MOB é de **cerca de 5 milhas náuticas, 9,3 km**. Erro de 12% contra um número que não entrou em nenhuma calibração — é a melhor evidência disponível de que o modelo está no lugar certo.

---

## 4. O preço do alcance: capacidade

O SF12 alcança o horizonte, mas paga em tempo de ar. Payload de 25 bytes, 8 canais, vazão máxima de ALOHA puro (18% do canal):

| SF | Tempo de ar | Msg/s úteis | Praticantes a 10 s | a 30 s | a 60 s |
|---|---|---|---|---|---|
| SF7 | 62 ms | 23,3 | **233** | 700 | 1400 |
| SF8 | 113 ms | 12,7 | 127 | 382 | 764 |
| SF9 | 206 ms | 7,0 | 70 | 210 | 420 |
| SF10 | 412 ms | 3,5 | 35 | 105 | 210 |
| SF11 | 823 ms | 1,7 | 17 | 52 | 105 |
| SF12 | 1483 ms | 1,0 | **10** | 29 | 58 |

**Um gateway em SF12 sustenta 10 praticantes a cada 10 segundos.** Em SF7, 233. A saída não é escolher um: é **taxa de espalhamento adaptativa** — quem está perto da praia fala em SF7 e quase não ocupa o canal; quem está longe sobe para SF12 e usa o alcance máximo. Como a maioria fica perto na maior parte do tempo, a capacidade média fica próxima do SF7-SF9, e o SF12 fica reservado para quem mais precisa dele. É exatamente o mecanismo ADR do LoRaWAN, e aqui ele deixa de ser otimização de bateria para virar **mecanismo de segurança**.

Segunda saída, complementar: em emergência o dispositivo muda de comportamento — sobe para SF12, aumenta a taxa e passa a ter prioridade. O canal é dimensionado para o dia normal e degrada com graça no dia ruim.

### 4.1 Enquadramento regulatório no Brasil

O Ato ANATEL nº 14448/2017 rege a radiação restrita. O Brasil adota o plano AU915, nas faixas **902–907,5 MHz e 915–928 MHz**, com potência de pico de até **1 W (30 dBm) para sistemas com 35 ou mais canais de salto** e 0,25 W (24 dBm) abaixo disso. O cálculo acima usou 20 dBm no vestível e 6 dBi no gateway — folgado dentro do limite. O módulo precisa de homologação ANATEL indicando essas faixas.

---

## 5. Custo por sessão de 4 horas

| Tecnologia | Fixes/sessão | Por sessão | Por mês (12 sessões) |
|---|---|---|---|
| Celular M2M (LTE-M), fix a cada 10 s | 1440 | R$ 0,00 | R$ 12 |
| **LoRa próprio, fix a cada 10 s** | 1440 | **R$ 0,00** | **R$ 0** (só CAPEX) |
| **NB-IoT NTN, fix a cada 10 s** | 1440 | **R$ 0,39** | **R$ 65** |
| Iridium SBD, fix a cada 5 min | 48 | R$ 14,40 | R$ 263 |
| Iridium SBD, fix a cada 10 s | 1440 | R$ 432,00 | inviável |

### 5.1 O que mudou no satélite

Este é o segundo achado do levantamento. O satélite era, até pouco tempo, sinônimo de "emergência apenas", porque o Iridium SBD cobra por mensagem — **R$ 432 por sessão** para rastreio de 10 em 10 segundos, o que encerra a conversa.

O **NB-IoT NTN** cobra por megabyte, na faixa de US$ 0,50 a 2,00. Um fix de 50 bytes a cada 10 segundos durante 4 horas dá 72 kB, ou **R$ 0,39 por sessão**. É mil vezes mais barato que o Iridium para a mesma taxa. Isso transforma o satélite de camada de último recurso em **camada de rastreio viável para os corredores de sombra** — Lençóis, Delta do Parnaíba, Cassino.

Com ressalvas honestas: a cobertura NTN ainda tem lacunas oceânicas e depende de autorização por país; em constelação GEO a latência é de ~270 ms e exige céu aberto; em LEO, 20 a 40 ms, mas com janelas de passagem. Antes de adotar, medir com hardware real no spot.

### 5.2 Direct-to-Device: projete para, não dependa de

A ANATEL aprovou em **2 de julho de 2026** a destinação secundária das faixas de 700, 850, 900, 1800, 1900/2100 e 2500 MHz para satélites que falam direto com celulares comuns. A área técnica tem até 90 dias para redigir as regras, e **a operação comercial não é esperada antes de 2027**, dependendo ainda de acordo com operadoras.

Quando chegar, resolve o problema dos corredores de sombra sem hardware adicional — o telefone que o praticante já tem passa a ter cobertura. A decisão de projeto hoje: manter a camada de transporte abstrata, para que o app troque de link sem reescrita.

---

## 6. Malha entre praticantes: por que não substitui a infraestrutura

Tentador: o pelotão de kitesurfistas é uma rede ad hoc móvel. Mas o cálculo mata a ideia como solução principal.

| Enlace | Alcance prático |
|---|---|
| Praticante → praticante, LoRa SF10 | **1,1 km** |
| Praticante → praticante, LoRa SF12 | **1,6 km** |

Com as duas antenas a 0,8 m da água, o horizonte seria 7,4 km, mas o orçamento entrega 1,6 km — as duas pontas sofrem perda de corpo e as duas estão coladas na superfície refletora.

Probabilidade de ter um vizinho ao alcance:

| Cenário | Alcance 1 km | Alcance 2 km |
|---|---|---|
| 30 praticantes num pico de 5 km² | 100% | 100% |
| 10 praticantes | 99,6% | 100% |
| 3 praticantes | 71,5% | 99,3% |
| **Praticante sozinho, derivando** | **0%** | **0%** |

**A malha funciona perfeitamente quando não é necessária e falha exatamente no caso que importa.** O acidente grave é o praticante que se afastou do pelotão, ou o último a sair da água ao fim da tarde. Malha entra como redundância barata, nunca como camada primária.

---

## 7. Tecnologias que não são rádio

Estas resolvem um problema que nenhuma das anteriores resolve: **monitorar quem não está carregando nada.**

### 7.1 Visão computacional a partir da praia
Uma câmera com teleobjetiva num mastro de 15 m, com detecção e rastreio de kites, conta quantos estão na água e alerta quando um kite cai e não sobe. Vantagem enorme: **não exige nada do praticante**. Limites reais: alcance útil de 1 a 2 km com boa óptica, degrada com contraluz, chuva e neblina, não funciona à noite, não dá identidade nem coordenada precisa. Serve como **contador e detector de anomalia**, não como fonte de coordenada para resgate.

### 7.2 Drone
Duas funções distintas, e vale não confundir:
- **Drone cativo como gateway elevado** — o cálculo da seção 3.2: leva o LoRa a 48,8 km. É a forma mais barata de comprar altura, e a única que se instala num spot sem obra.
- **Drone de resgate** — o FDNY já usa em Rockaway Beach para lançar boias infláveis a banhistas, com duas boias lançadas na ocorrência mais recente. Não é rastreio: é o braço de resposta, e encurta o tempo até a vítima ter flutuação.

### 7.3 Radar
X-band marítimo enxerga embarcação, mas uma pessoa na água tem seção reta minúscula e some no clutter de mar. O kite é grande, porém é tecido, e reflete mal. Não recomendo como camada de detecção — o custo é alto e a taxa de detecção, ruim.

---

## 8. Arquitetura recomendada, revisada

O levantamento muda a recomendação anterior. Não é "celular com LoRa de redundância" — é o contrário.

| Camada | Tecnologia | Cobre | Custo recorrente |
|---|---|---|---|
| **Primária no spot** | **LoRa próprio com gateway elevado**, SF adaptativo | 26 km com mastro de 30 m; 45 km em duna ou drone cativo | zero |
| Secundária | Celular do telefone (LTE) | 8 km, e serve para app, mapa e voz | franquia |
| Corredor de sombra | NB-IoT NTN | onde não há nem gateway nem torre | R$ 0,39/sessão |
| Emergência independente | PLB 406 MHz e AIS-MOB do praticante | global e 10 km até estação própria | zero |
| Complemento | Malha entre praticantes; visão computacional na praia | pelotão; quem não carrega nada | zero |
| Resposta | Drone com boia inflável | primeiros minutos | — |

O dispositivo passa a ser **LoRa primário com LTE-M oportunista**, e não o contrário. Isso inverte a decisão de hardware da Fase 7 do projeto: o módulo de referência deixa de ser apenas nRF9160 ou SARA-R5 e passa a ser **um SX126x com GNSS, e opcionalmente um modem celular** para quando houver rede.

---

## 9. O que precisa ser medido antes de fechar

Nenhum destes números substitui campo. Ensaios, em ordem de valor:

1. **Ensaio LoRa de alcance** — um gateway no ponto mais alto disponível do spot piloto e um nó no arnês do praticante, registrando RSSI, SNR e SF por posição. Confirma ou derruba os 26 km. Custo: um gateway e dois nós, menos de R$ 3 mil.
2. **Ensaio de capacidade** — 20 nós transmitindo juntos, medindo taxa de entrega por SF. Valida a tabela da seção 4.
3. **Ensaio de perda por corpo** — o mesmo nó no braço, no colete e submerso, com o gateway fixo. Mede os 10 dB assumidos, que são o parâmetro mais incerto de todo o modelo.
4. **Ensaio NTN** — um módulo NB-IoT NTN no spot de sombra, medindo tempo até o primeiro fix e taxa de entrega ao longo do dia.
5. **Ensaio de drone cativo** — gateway embarcado a 100 m, comparando com o gateway de mastro.

---

## 10. Fontes

**LoRa sobre o mar**
- Experimental Study of LoRa Transmission over Seawater: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6163321/
- LPWAN at Sea — LoRaWAN para monitoramento marinho: https://pmc.ncbi.nlm.nih.gov/articles/PMC6679513/
- Unveiling LoRa's Oceanic Reach — rede dos Açores, >130 km: https://doi.org/10.3390/s23177394
- Recorde de 1300 km sobre o mar: https://www.mwrf.com/technologies/communications/wireless/article/21273819/microwaves-rf-the-lorawan-distance-world-record-now-over-1300-kilometers

**Satélite**
- 3GPP — NTN nas Releases 17 e 18: https://www.3gpp.org/news-events/partner-news/ntn-rel17
- u-blox — Satellite IoT for NTN: https://www.u-blox.com/en/technologies/ntn
- Ground Control — o que 2026 significa para o IoT via satélite padronizado: https://www.groundcontrol.com/blog/what-2026-looks-like-standards-based-satellite-iot/
- Sateliot: https://sateliot.space/ · Myriota: https://myriota.com/myriota-expands-global-satellite-iot-network/
- ANATEL destina faixas para Direct-to-Cell (2 jul 2026): https://www.riotimesonline.com/starlink-direct-to-cell-anatel-brazil-satellite-2026/
- Análise da decisão da ANATEL: https://consumidormoderno.com.br/stalink-celular-anatel-brasil/

**Regulação**
- ANATEL, Ato nº 14448/2017 — radiação restrita: https://informacoes.anatel.gov.br/legislacao/atos-de-certificacao-de-produtos/2017/1139-ato-14448
- Homologação de módulos IoT (LoRaWAN, NB-IoT): https://abcpcertificacao.com.br/certificacao-anatel/modulos-iot/

**Drone e visão**
- FDNY resgata banhistas com drone em Rockaway Beach: https://www.surfer.com/news/fdny-drones-rescue-swimmers-new-york-rockaway-beach
- Vigilância marítima com drone cativo e IA: https://www.mdpi.com/2504-446X/10/4/268
