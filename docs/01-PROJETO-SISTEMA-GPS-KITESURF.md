# Projeto: Sistema de Localização GPS e Resgate para Esportes Aquáticos de Vento

**Codinome:** GUARDIAN-KITE
**Domínio:** kitesurf, wingfoil, windsurf, SUP, natação em águas abertas, surf downwind
**Status:** especificação — nada implementado (por decisão do solicitante)
**Data:** 2026-08-28

---

## 0. Sumário executivo

Sistema de monitoramento em tempo real de praticantes de esportes de vento na água, composto por:

1. **Dispositivo vestível** (ou o próprio smartphone/relógio, no MVP) que emite posição GNSS continuamente;
2. **Backend de ingestão e processamento** que recebe, valida, armazena e avalia cada ponto contra regras;
3. **Motor de barreiras (geofences)** — zonas seguras, de alerta e proibidas, incluindo barreiras dinâmicas que se contraem quando o vento vira offshore;
4. **Motor de alertas e escalonamento** — do próprio praticante até o acionamento do SAR oficial;
5. **Painel de resgate (Rescue Console)** — a tela que o salva-vidas / escola / SALVAMAR abre para receber coordenadas prontas para busca, incluindo projeção de deriva.

### Princípio de segurança inegociável

> Este sistema **não substitui** equipamento de salvamento certificado (PLB 406 MHz / Cospas-Sarsat, AIS-MOB, colete, leash, rádio VHF).
> Ele é uma **camada de redução de tempo de incerteza** — o mesmo papel que o Coast Guard SafeTrx cumpre oficialmente.
> Todo material de marketing, onboarding do app e contrato devem afirmar isso explicitamente. Prometer "resgate garantido" cria risco de morte e responsabilidade civil/criminal.

---

## 1. Benchmarking — o que já existe e está em operação

### 1.1 Categorias do mercado

| Categoria | Exemplos | Como funciona | Custo típico | Limitação crítica |
|---|---|---|---|---|
| **Balizas SAR por satélite (PLB/EPIRB)** | Ocean Signal rescueME PLB1/PLB3, ACR ResQLink | 406 MHz → Cospas-Sarsat → MRCC nacional. 24h+ de transmissão, cobertura global | US$ 300–450, sem mensalidade | **Só liga/desliga.** Não há rastreio contínuo, não há prevenção, não avisa amigos. Ativação manual (3 passos) — difícil com uma mão, na água, em pânico |
| **Balizas AIS-MOB** | Ocean Signal rescueME MOB1 | VHF marítimo → receptores AIS de barcos num raio de ~5 milhas náuticas; dispara alarme DSC | US$ 300–400 | Só funciona se houver **barco com AIS por perto**. Numa praia de kite sem tráfego, não alerta ninguém |
| **Comunicadores de satélite bidirecionais** | Garmin inReach Mini 2 (Iridium, global), ZOLEO (Iridium), SPOT X (Globalstar, ~60% do globo) | Tracking periódico + mensagens + SOS para central 24/7 (IERCC) | US$ 150–400 + US$ 15–65/mês | Volumoso para arnês de kite, tracking com intervalos de minutos, não tem geofence de praia nem lógica esportiva. Mini 2 fixa satélite em 30–60s; SPOT X em 60–120s |
| **Plataformas SAR com smartphone** | **Coast Guard SafeTrx / RYA SafeTrx / RNLI** (8 West, desde 2013, ~10 países, ~250 mil usuários) | App envia posição/velocidade/rumo periodicamente ao servidor; "Sail Plan" com ETA; se o ETA estoura, escalona: notifica o usuário → SMS aos contatos → Guarda Costeira acessa o histórico em servidor seguro | Gratuito (financiado por Guarda Costeira/associações) | Feito para navegação, não para kite. Depende de bateria e cobertura celular do telefone. Sem barreiras dinâmicas por vento |
| **Trackers dedicados a esportes de vento** | **NAUTITRACK** (bracelete, €399 + €72/ano), **GPT – Gpacers Poseidon Tracker** (rádio + GPS + internet + satélite LEO, com alerta de fronteira, colisão, perda de sinal e check de 5 min) | Transmissão contínua de posição inclusive longe da costa; alerta a familiares | €400 + assinatura | Ecossistema fechado, sem integração com SAR oficial local, sem console de resgate para salva-vidas |
| **Apps de log/performance (não são segurança)** | Hoolan, WindsportTracker, gps-kitesurfing, Surfr, WOO | Gravam a sessão (velocidade, saltos, track) via relógio ou telefone | Grátis / freemium | **Não são sistemas de resgate.** Track só é lido depois da sessão |
| **Plataformas GPS genéricas open-source** | **Traccar** (Java, >200 protocolos, >2000 modelos de dispositivo, geofences Circle/Polygon/Polyline com eventos de entrada/saída, REST API, SQL, self-hosted/Docker) | Servidor recebe de qualquer tracker, aplica geofences, dispara eventos | Grátis (GPL) / cloud paga | Feito para frota terrestre: sem modelo de deriva, sem MOB, sem escalonamento SAR, sem lógica marítima |

### 1.2 Observação do funcionamento — o que copiar

Do estudo dos sistemas acima, os **padrões comprovados** que devem ser replicados:

- **SafeTrx — "Sail Plan + ETA + escalonamento automático":** o usuário declara antes de entrar na água *onde vai, com quem e até quando*. Se não fechar o plano, a máquina de escalonamento roda sozinha. **Isto encurta a "fase de incerteza"** — que é o que mais mata em SAR. É o padrão de ouro e deve ser o coração do nosso sistema.
- **SafeTrx — acesso do SAR a um servidor seguro:** a Guarda Costeira não recebe um print de WhatsApp; ela abre um console com o histórico completo. Nosso *Rescue Console* copia isso.
- **GPT Poseidon — "check de pessoal por contagem regressiva de 5 minutos":** se o sistema suspeita de incidente, ele **pergunta** ao praticante e só escala se não houver resposta. Reduz drasticamente o falso positivo (o maior inimigo de qualquer sistema de alarme).
- **GPT Poseidon — múltiplos meios redundantes** (rádio + celular + satélite LEO) com degradação graciosa.
- **Traccar — geofences como entidade de primeira classe** com Circle/Polygon/Polyline e eventos de entrada/saída, e uma API REST limpa. Arquitetura de referência para o nosso motor de barreiras.
- **PLB/Cospas-Sarsat — formato e disciplina do alerta:** identificação registrada do portador, posição, hora, e transmissão contínua por 24h. O nosso pacote de emergência deve carregar os mesmos campos.
- **inReach — confirmação bidirecional:** a vítima precisa **saber** que o socorro foi acionado. Alerta unidirecional gera pânico e decisões ruins (ex.: largar o equipamento e nadar).

### 1.3 Lacunas encontradas — onde o projeto aprimora

| # | Lacuna do mercado | Aprimoramento proposto |
|---|---|---|
| A1 | Nenhum sistema entende **kitesurf**: perder o kite = perder a propulsão = deriva imediata | Detecção de eventos específicos: *kite loop / queda longa*, **separação praticante↔prancha**, ausência de movimento, velocidade zero com deriva |
| A2 | Barreiras estáticas; ninguém considera que **vento offshore transforma a mesma linha d'água numa armadilha** | **Barreira dinâmica**: o polígono seguro se contrai automaticamente quando o vento tem componente offshore acima de X kt, e a zona de alerta se desloca a favor da deriva prevista |
| A3 | A última posição conhecida é tratada como a posição atual | **Datum de busca com modelo de deriva (Leeway, Allen & Plourde 1999/2005 — mesmo modelo usado por SAROPS/EUA, MOTHY/França, CANSARP/Canadá)**: o console mostra elipse de probabilidade crescendo com o tempo, não um pino fixo |
| A4 | Alerta chega como notificação genérica de app | **Pacote de resgate pronto para rádio**: coordenadas em DD° MM.mmm′ (padrão SAR) + decimal + MGRS, hora UTC e local, precisão em metros, idade do fix, rumo/velocidade, descrição física do praticante e cor do kite/prancha |
| A5 | Escola/salva-vidas não tem visão coletiva | **Painel de praia multi-praticante** com semáforo por atleta, contagem de quem entrou e quem saiu da água |
| A6 | Sem cobertura celular = sem nada | **Store-and-forward**: dispositivo grava offline e faz burst ao reconectar; opcionalmente relay LoRa a partir de gateway na praia (alcance típico 15 km em área aberta, e o mar é a melhor linha de visada possível) |
| A7 | Falso positivo destrói a confiança | **Escada de confirmação** de 3 degraus antes de acionar terceiros (auto-check no dispositivo → buddy → base) |
| A8 | Dados de localização tratados sem cuidado legal | Privacidade por projeto: LGPD, dado de geolocalização é dado pessoal sensível na prática; consentimento granular, retenção curta, quebra de sigilo só em emergência ativa (interesse vital, art. 7º, IV/VIII e art. 11 da LGPD) |

---

## 2. Requisitos

### 2.1 Requisitos funcionais (RF)

**Cadastro e preparação**
- RF-01 Cadastro do praticante com ficha de resgate: nome, foto, altura/peso, cor de roupa/lycra/colete, cor e tamanho do kite, tipo de prancha, contatos de emergência, condições médicas relevantes.
- RF-02 Cadastro de spots (praias) com polígono operacional, ponto de entrada na água, pontos de resgate por terra e por barco, rampa de acesso, canal de VHF local, telefones do SAR local.
- RF-03 Plano de sessão ("Sail Plan"): spot, horário previsto de retorno (ETA), buddy, equipamento em uso.
- RF-04 Check-in (entrada na água) e check-out (saída) explícitos, com confirmação.

**Rastreamento**
- RF-05 Emissão de posição com taxa adaptativa: 1 s (emergência), 5–10 s (em água, normal), 60 s (repouso/praia), pausa (dispositivo em terra e parado).
- RF-06 Cada ponto carrega: lat, lon, timestamp UTC, precisão horizontal (m), altitude/velocidade/rumo, nº de satélites, HDOP, nível de bateria, origem do fix (GNSS/rede), flag de dado offline recuperado.
- RF-07 Buffer offline com no mínimo 8 h de pontos e reenvio automático ordenado ao restabelecer link.
- RF-08 Visualização em tempo real em mapa (web e mobile) com rastro, vetor de rumo e círculo de precisão.

**Barreiras (geofences)**
- RF-09 Tipos: círculo, polígono, corredor (polilinha com raio), e *setor* (arco a partir de um ponto).
- RF-10 Classes de barreira: **Zona Segura** (dentro = ok), **Zona de Atenção** (aviso), **Zona Proibida/Perigo** (canal de navegação, pedral, área de tubarão, foz), **Limite Máximo Absoluto** (linha de não-retorno).
- RF-11 Regras de disparo: entrada, saída, permanência acima de N minutos, aproximação (distância < X m da borda com rumo de aproximação).
- RF-12 Barreira dinâmica: parâmetros recalculados a cada ciclo em função de vento (direção/intensidade), maré/corrente e horário (pôr do sol).
- RF-13 Barreira pessoal: raio máximo individual por nível do praticante (iniciante 300 m, intermediário 1 km, avançado 3 km, downwind = corredor).

**Detecção de incidente**
- RF-14 Detectores: (a) inatividade — velocidade < 0,5 kt por > 3 min em água; (b) deriva — movimento coerente com corrente/vento sem propulsão; (c) saída de barreira; (d) perda de sinal > N min; (e) bateria crítica; (f) queda brusca de aceleração / impacto; (g) botão de pânico (físico e no app); (h) ETA do plano estourado.
- RF-15 Confirmação ativa: ao suspeitar, o dispositivo vibra/apita e abre janela de resposta de 60–180 s ("Você está bem?"). Sem resposta → escala.

**Alertas e escalonamento**
- RF-16 Escada de escalonamento configurável por spot, padrão:
  1. **N0 — auto-verificação** no dispositivo (60–180 s).
  2. **N1 — buddy/parceiro de sessão** (push + som).
  3. **N2 — base/escola/salva-vidas** (push, SMS, som contínuo no painel de praia).
  4. **N3 — contatos de emergência** (SMS + ligação por voz sintetizada com as coordenadas).
  5. **N4 — SAR oficial**: pacote pronto para acionamento do **SALVAMAR (Marinha, 185)** / **Bombeiros (193)** / **SAMU (192)**, com o MRCC/sub-região correta do spot (SALVAMAR Norte–Belém, Nordeste–Natal, Leste–Salvador, Sueste–Rio, Sul Sueste–São Paulo, Sul–Rio Grande; supervisão SALVAMAR BRASIL/MRCC Brazil no Rio).
- RF-17 Cancelamento de alerta com autenticação (evitar cancelamento acidental) e registro de quem cancelou.
- RF-18 Todo alerta gera **incidente** com linha do tempo imutável (audit log) — quem foi avisado, quando, por qual canal, quem confirmou.

**Console de resgate**
- RF-19 Tela dedicada por incidente: última posição confiável, idade do fix, elipse de deriva projetada (15/30/60 min), rastro das últimas 2 h, ficha do praticante, condições meteo-oceanográficas no momento.
- RF-20 Botão "copiar pacote SAR" (texto pronto para ditar em rádio) e exportação GPX/KML para a embarcação de resgate.
- RF-21 Modo navegação para o resgatista: rumo e distância até o alvo, atualizado se o alvo voltar a transmitir.

### 2.2 Requisitos não-funcionais (RNF)

- RNF-01 **Latência fim-a-fim** (fix → visível no console) ≤ 5 s no p95 com cobertura celular.
- RNF-02 **Disponibilidade** do backend ≥ 99,9 %; caminho de emergência (ingestão + alerta) com degradação graciosa independente do resto (se o mapa cair, o SMS ainda sai).
- RNF-03 **Autonomia**: ≥ 6 h em modo sessão; ≥ 24 h em modo emergência com transmissão reduzida.
- RNF-04 **Estanqueidade** IP68 / IPX8 (imersão), resistência a impacto e à água salgada, flutuante ou fixado a item flutuante.
- RNF-05 **Segurança**: TLS 1.3 em todo transporte, mTLS ou token por dispositivo, dados em repouso cifrados, RBAC (praticante / buddy / escola / salva-vidas / SAR / admin).
- RNF-06 **Privacidade/LGPD**: minimização, retenção padrão de 90 dias para tracks, anonimização para estatística, exportação e exclusão a pedido, DPO designado, RIPD (relatório de impacto) formal.
- RNF-07 **Observabilidade**: métricas de saúde por dispositivo (último contato, bateria, qualidade do fix) e alarme quando a **própria plataforma** perde a capacidade de alertar (dead man's switch do sistema).
- RNF-08 **Escala alvo do MVP**: 500 dispositivos simultâneos, 1 ponto/5 s = 100 msg/s; arquitetura preparada para 10 000 (2 000 msg/s).
- RNF-09 **Offline-first no app**: mapa do spot em cache, funcionamento sem rede, fila persistente.
- RNF-10 **Acessibilidade e usabilidade em condição real**: leitura sob sol forte, operação com uma mão, luvas/frio, botão de pânico tátil sem olhar.

### 2.3 Requisitos de segurança de vida (safety)
- SAF-01 Nenhuma funcionalidade nova pode aumentar a latência do caminho de emergência. Caminho crítico isolado e testado a cada release.
- SAF-02 Falha de qualquer componente não crítico não pode impedir o alerta (fail-safe, não fail-silent).
- SAF-03 Todo alerta suprimido/deduplicado deve ser registrado com justificativa.
- SAF-04 Ensaio de campo obrigatório antes de qualquer release que toque o caminho crítico.

---

## 3. Arquitetura do sistema

### 3.1 Visão em camadas

```
[1] BORDA (na água)
    ├─ App mobile (iOS/Android) + Apple Watch / Garmin  ← MVP
    ├─ Tracker dedicado LTE-M/NB-IoT + GNSS (nRF9160 / u-blox SARA-R5)  ← Fase 2
    └─ Baliza certificada do praticante (PLB / AIS-MOB)  ← camada independente, não integrada
                │  MQTT/TLS  ·  HTTPS batch  ·  SMS fallback  ·  LoRa (opcional)
                ▼
[2] INGESTÃO
    ├─ Broker MQTT (EMQX/Mosquitto) + API REST de ingestão
    ├─ Autenticação por dispositivo, validação e normalização de esquema
    └─ Fila/stream (Kafka ou Redis Streams no MVP)
                ▼
[3] PROCESSAMENTO EM TEMPO REAL
    ├─ Motor de Barreiras (PostGIS: ST_Contains / ST_DWithin / ST_Distance)
    ├─ Motor de Detecção de Incidente (regras + janelas temporais)
    ├─ Enriquecimento meteo-oceanográfico (vento, onda, maré, corrente)
    └─ Motor de Deriva (Leeway) para datum de busca
                ▼
[4] PERSISTÊNCIA
    ├─ PostgreSQL + PostGIS + TimescaleDB (série temporal de posições)
    ├─ Redis (estado quente: última posição, estado de cada barreira por atleta)
    └─ Object storage (tracks arquivados, evidências, logs de incidente)
                ▼
[5] ALERTA E ESCALONAMENTO
    ├─ Máquina de estados de incidente (N0→N4) com timers persistentes
    └─ Canais: Push (FCM/APNs), SMS, voz (TTS), e-mail, webhook, sirene no painel
                ▼
[6] APRESENTAÇÃO
    ├─ App do praticante   ├─ Painel de praia (escola/salva-vidas)
    ├─ Rescue Console (SAR)  └─ Admin / auditoria
```

### 3.2 Decisão de conectividade (matriz)

| Tecnologia | Alcance real do mar | Latência | Consumo | Custo/mês | Papel no projeto |
|---|---|---|---|---|---|
| **4G/LTE + LTE-M/NB-IoT** | 5–15 km da costa (torre alta, linha de visada sobre a água) | segundos | médio/baixo | R$ 5–20 (M2M) | **Primário.** LTE-M lida com handoff entre torres, ideal para alvo em movimento; NB-IoT é mais econômico mas pior em mobilidade |
| **LoRaWAN (gateway próprio na praia)** | ~15 km em área aberta; sobre o mar tende ao melhor caso | segundos | muito baixo | ~zero após CAPEX | **Redundância** onde não há celular; gateway elevado no clube/escola |
| **Satélite (Iridium/Globalstar, ou IoT LEO)** | global (Iridium) / ~60 % do globo (Globalstar) | 30–120 s para fixar | alto | US$ 15–65 | **Fase 3**, para downwind longo e mar aberto |
| **AIS-MOB / VHF** | ~5 NM até barcos com AIS | imediato | — | — | Camada independente recomendada ao usuário, não integrada |
| **PLB 406 MHz Cospas-Sarsat** | global | minutos | — | sem mensalidade | Camada independente **recomendada como obrigatória** em travessias |

**Decisão:** MVP em **celular (smartphone)**, produto em **LTE-M com fallback SMS**, e **LoRa como redundância de praia**. Satélite só para o produto "expedição".

### 3.3 Motor de barreiras — desenho

- Barreiras armazenadas como `geography(Polygon|LineString|Point, 4326)` no PostGIS, com índice GiST.
- Avaliação por ponto: `ST_Contains(zona, ponto)` para dentro/fora; `ST_Distance(::geography)` para "distância até a borda"; `ST_DWithin` para proximidade.
- Estado por (atleta × barreira) em Redis: `INSIDE | OUTSIDE | APPROACHING`, com histerese (buffer de ~25 m) e debounce (2 fixes consecutivos) para não gerar alarme por ruído de GPS.
- Barreira dinâmica: job a cada 5 min lê vento/maré e recalcula o polígono efetivo = `ST_Buffer(base, -f(vento_offshore))`, versionado (toda alteração fica no histórico, para auditoria de incidente).

### 3.4 Motor de deriva (o diferencial)

Após a última posição conhecida, a busca não é um ponto — é uma área que cresce:

```
datum(t) = última_posição
         + ∫ [ corrente_superficial + leeway(vento) ] dt
raio_de_incerteza(t) = erro_do_fix + erro_do_modelo·t + dispersão_Monte_Carlo
```

- Coeficientes de leeway para *person-in-water* (PIW) conforme Allen & Plourde — base do IAMSAR e dos sistemas SAROPS/MOTHY/CANSARP.
- Simulação Monte Carlo (N=1000 partículas) → mapa de calor de probabilidade + elipse de 50 %/95 %.
- Fonte de dados: previsão de vento/corrente (Open-Meteo Marine, Copernicus Marine, HYCOM) + estação local se houver.
- **Saída para o resgatista:** "Área de busca sugerida em 30 min: elipse centrada em XX°XX.XXX′ S, XX°XX.XXX′ W, eixo maior 800 m, orientação 210°."

---

## 4. Etapas do projeto (fases)

| Fase | Nome | Duração estimada | Entregável principal |
|---|---|---|---|
| **F0** | Descoberta e segurança | 2–3 sem | Documento de requisitos validado com salva-vidas, escolas e (idealmente) contato na Capitania/SALVAMAR |
| **F1** | Arquitetura e provas de conceito | 2–3 sem | ADRs, PoC de ingestão MQTT, PoC de geofence PostGIS, teste de cobertura celular no spot alvo |
| **F2** | Backend núcleo | 4–6 sem | Ingestão + persistência + API + motor de barreiras + auditoria |
| **F3** | Motor de incidente e escalonamento | 3–4 sem | Máquina de estados N0–N4, canais push/SMS/voz, testes de falso positivo |
| **F4** | App do praticante | 4–6 sem | Check-in/out, plano de sessão, tracking em background, botão de pânico, offline |
| **F5** | Painel de praia + Rescue Console | 3–4 sem | Visão coletiva, incidente, pacote SAR, exportação GPX/KML |
| **F6** | Motor de deriva | 2–3 sem | Datum + elipse de busca validados contra caso real/simulado |
| **F7** | Hardware dedicado (opcional) | 8–12 sem | Protótipo LTE-M IP68 + homologação |
| **F8** | Testes de campo e homologação operacional | 3–4 sem | Relatório de ensaios, protocolo operacional assinado com a escola/salva-vidas |
| **F9** | Piloto controlado | 4–8 sem | 1 spot, 20–50 praticantes, métricas de confiabilidade |
| **F10** | Operação e melhoria contínua | contínuo | SLO, pós-mortem de cada incidente, roadmap |

---

## 5. Stack recomendado

| Camada | Escolha | Justificativa |
|---|---|---|
| Ingestão | **EMQX** (MQTT 5, TLS, autenticação por dispositivo) | padrão IoT, retenção de sessão, QoS 1 |
| Stream | **Redis Streams** (MVP) → **Kafka** (escala) | simplicidade primeiro, caminho de crescimento claro |
| Banco | **PostgreSQL + PostGIS + TimescaleDB** | geoprocessamento + série temporal no mesmo motor, hypertables com retenção automática |
| Backend | **Go** (ingestão/motor, baixa latência) ou **Node/TypeScript**; **Python** para o motor de deriva | separação entre caminho crítico e analítico |
| API | REST + **WebSocket** para tempo real | Traccar valida REST; WS para o mapa vivo |
| Mapa | **MapLibre GL** + tiles náuticos (OpenSeaMap) | offline-capable, sem lock-in |
| App | **React Native** ou **Flutter** + módulos nativos de background location | background location exige código nativo de qualidade em ambas as plataformas |
| Notificação | FCM/APNs + Twilio (SMS/voz) + fallback de operadora local | voz sintetizada é o canal que acorda alguém às 4h |
| Infra | Docker/K8s, IaC (Terraform), observabilidade (Prometheus + Grafana + Loki) | reprodutibilidade e auditoria |
| Alternativa de atalho | **Traccar** como base de ingestão/protocolos | ganha 2000+ modelos de tracker de graça; escrever por cima o motor de incidente/deriva |

---

## 6. Modelo de dados (núcleo)

```
athlete(id, nome, foto, altura, peso, nivel, cor_lycra, cor_kite, tam_kite, obs_medica, contatos[])
device(id, athlete_id, tipo, imei/uuid, bateria, firmware, ultimo_contato)
spot(id, nome, poligono_operacional, ponto_entrada, pontos_resgate[], canal_vhf, telefones_sar[])
geofence(id, spot_id, nome, classe, geometria, regra, ativa, versao, valido_de, valido_ate)
session(id, athlete_id, spot_id, buddy_id, eta, inicio, fim, status)
position(time, device_id, geom, precisao_m, vel, rumo, sats, hdop, bateria, origem, offline_flag)  -- hypertable
geofence_state(athlete_id, geofence_id, estado, desde)
incident(id, athlete_id, session_id, tipo, nivel_atual, aberto_em, fechado_em, resolucao)
incident_event(incident_id, ts, ator, acao, canal, payload)   -- imutável
drift_estimate(incident_id, ts_alvo, datum_geom, elipse_geom, prob)
weather_snapshot(spot_id, ts, vento_dir, vento_kt, rajada, onda_m, mare_m, corrente_dir, corrente_kt)
```

---

## 7. Regulatório, legal e ético (Brasil)

- **ANATEL:** todo produto de hardware com rádio (LTE/LoRa) exige **homologação**; usar módulos já homologados reduz o processo. Chip M2M exige plano de dados adequado.
- **Marinha do Brasil / Capitania dos Portos:** o acionamento SAR é do **SALVAMAR (185)**; o sistema deve *facilitar* o acionamento, nunca substituí-lo ou intermediá-lo sem acordo formal. Buscar interlocução com a Capitania local antes do piloto.
- **PLB/EPIRB:** balizas 406 MHz devem ser registradas junto à autoridade competente; orientar o usuário.
- **LGPD:** geolocalização em tempo real é dado pessoal de alto risco. Necessário: base legal explícita (consentimento + tutela da vida em emergência), RIPD, política de retenção, minimização, controle de compartilhamento com terceiros (escola, buddy), direito de exclusão, DPO.
- **Menores de idade:** consentimento do responsável, regras específicas de compartilhamento.
- **Responsabilidade civil:** termos de uso com limitação clara, seguro de responsabilidade civil, e o aviso de "não substitui equipamento de salvamento" em todas as telas de onboarding.
- **Normas de referência:** IAMSAR (manual internacional de busca e salvamento) para vocabulário, formato de coordenadas e procedimento; ISO 26262 não se aplica, mas IEC 61508 (SIL) serve de inspiração para o caminho crítico.

---

## 8. Riscos principais

| Risco | Impacto | Mitigação |
|---|---|---|
| Falso positivo em massa | Perda de confiança → sistema ignorado → morte | Escada de confirmação, histerese, tuning com dados reais de sessões |
| Falso negativo (não detecta acidente real) | Morte | Múltiplos detectores independentes; ETA/Sail Plan como rede final; nunca depender de um único sinal |
| Bateria do celular acaba | Perda de rastreio | Aviso em 30 %/15 %, modo economia automático, recomendação de power bank estanque, hardware dedicado na Fase 7 |
| Sem cobertura celular no spot | Sistema inútil | Medição de cobertura por spot **antes** de habilitar; gateway LoRa; rótulo honesto de cobertura no app |
| Usuário confia demais e assume mais risco | Aumenta acidentes | Design anti-complacência: o app **não** diz "você está seguro"; diz "monitorado, com limitações X, Y, Z" |
| Vazamento de dados de localização | Dano à privacidade, stalking | Criptografia, RBAC, retenção curta, sem venda de dados, log de acesso |
| Indisponibilidade do backend em dia de vento forte (pico) | Falha justo quando mais importa | Autoscaling, teste de carga com 3× o pico, caminho de emergência isolado |

---

## 9. Custos estimados (ordem de grandeza)

**MVP baseado em smartphone (F0–F6, F8, F9)**
- Equipe: 1 backend, 1 mobile, 1 front/geo, 1 PM/PO parcial → ~5–7 meses
- Infra: R$ 400–1.200/mês (1 VM média + banco + object storage)
- SMS/voz: R$ 0,10–0,60 por alerta
- Dados meteo-oceanográficos: gratuito (Open-Meteo) a R$ 0/500 mês (Copernicus)

**Hardware dedicado (F7)** — BOM alvo por unidade em lote de 1000:
- Módulo nRF9160 ou SARA-R510M8S: US$ 18–30
- Antena GNSS + LTE, PMIC, bateria LiPo 1000–2000 mAh: US$ 12–20
- Caixa IP68 + botão estanque + buzzer + acelerômetro: US$ 15–25
- **Total ~US$ 50–80/unid.** + NRE de projeto/certificação US$ 25–60 k
- Referência de mercado: NAUTITRACK €399 + €72/ano

---

## 10. Métricas de sucesso (SLO)

- **Tempo de detecção** (evento real → incidente aberto): p95 ≤ 3 min.
- **Tempo até N4** (incidente → pacote SAR pronto): ≤ 60 s após decisão.
- **Taxa de falso positivo**: ≤ 1 por 200 sessões, e nenhum que chegue a N4.
- **Cobertura de rastreio**: ≥ 98 % dos segundos de sessão com fix válido em spot habilitado.
- **Erro do datum de deriva** em 30 min: ≤ 300 m no teste com boia derivante.
- **Disponibilidade do caminho crítico**: ≥ 99,95 %.

---

## 11. Fontes da pesquisa de benchmarking

**Sistemas SAR e balizas**
- Salvamar Brasil / MRCC Brazil — estrutura SAR e contatos: https://www.marinha.mil.br/salvamarbrasil/
- Ocean Signal — AIS MOB vs PLB vs EPIRB: https://oceansignal.com/news/boating-emergency-essentials-how-ais-mob-plb-and-epirb-can-save-your-life-on-the-water/
- AIS MOB versus PLB: A User's Guide (Seas of Solutions): https://www.seasofsolutions.com/wp-content/uploads/2024/05/AIS-MOB-vs-PLB-v10-A4-12-05-24.pdf

**Plataformas de tracking com integração SAR**
- Coast Guard SafeTrx: https://www.safetrxapp.com/
- RNLI / Thanet — como o SafeTrx funciona e escalona: https://thanetrnlicommunitysafety.org.uk/what-exactly-is-safetrx-and-how-can-it-keep-me-safe/

**Comunicadores de satélite**
- Garmin inReach Mini 2 vs SPOT X (CNN Underscored): https://www.cnn.com/cnn-underscored/reviews/garmin-inreach-mini-2-vs-spot-x
- ZOLEO vs inReach — comparativo: https://www.adventurealan.com/best-satellite-communicator-zoleo-vs-inreach/

**Trackers dedicados a esportes de vento**
- NAUTITRACK (bracelete GPS para paddle/kite/wing): https://www.boatnews.com/story/48818/gps-tracker-for-paddle-kitesurf-and-wingfoil-nautitrack-a-newcomer-on-the-scene
- GPT — Gpacers Poseidon Tracker: https://apps.apple.com/us/app/id1446755315
- Hoolan (tracking de sessão): https://www.hoolan.app/
- WindsportTracker: https://www.windsporttracker.com/

**Plataforma open-source de referência**
- Traccar (>200 protocolos, geofences, REST API): https://www.traccar.org/ · https://github.com/traccar/traccar

**Arquitetura técnica**
- HiveMQ — geofencing dinâmico com MQTT: https://www.hivemq.com/blog/dynamic-geo-fencing-building-location-aware-iot-applications-with-mqtt-hivemq/
- TimescaleDB + PostgreSQL: https://oneuptime.com/blog/post/2026-01-27-timescaledb-postgresql-extensions/view
- Sinay — protocolos IoT marítimos (LoRa vs NB-IoT vs satélite): https://sinay.ai/en/maritime-iot-protocol-wars-lora-vs-nb-iot-vs-satellite-mesh-in-real-world-deployments/

**Hardware**
- Nordic nRF9160 (LTE-M/NB-IoT + GNSS): https://www.nordicsemi.com/Products/nRF9160
- u-blox SARA-R5: https://www.digikey.com/en/product-highlight/u/u-blox/sara-r5-lte-m-nb-iot-modules

**Modelo de deriva (datum de busca)**
- Predicting drift characteristics of persons-in-the-water: https://www.sciencedirect.com/science/article/abs/pii/S0029801821014554
- Validação de previsão de trajetória com OpenDrift para SAR: https://www.joet.org/journal/view.php?number=3110
- Drift Trajectory Prediction for Multiple-Persons-in-Water (MDPI): https://www.mdpi.com/2077-1312/14/2/144
