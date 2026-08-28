# CHECKLIST COMPLETO DE MONTAGEM — Sistema GPS de Monitoramento e Resgate (GUARDIAN-KITE)

> Marque item a item. Nenhuma fase avança com item **[CRÍTICO]** em aberto.
> Legenda: `[CRÍTICO]` = bloqueia release · `[SAFETY]` = envolve risco de vida · `[LEGAL]` = obrigação regulatória

---

## FASE 0 — DESCOBERTA, SEGURANÇA E VALIDAÇÃO DE CAMPO

### 0.1 Definição de escopo
- [ ] Definir esportes atendidos no MVP (kitesurf / wingfoil / windsurf / SUP / travessia)
- [ ] Definir o **spot piloto** único (uma praia, um clube, um grupo)
- [ ] Definir persona primária: praticante solo, escola com alunos, ou clube com salva-vidas
- [ ] Definir o que o sistema **NÃO** faz (lista escrita e publicada) `[SAFETY]`
- [ ] Escrever a declaração oficial: "não substitui PLB/AIS-MOB/colete/leash" `[SAFETY]` `[CRÍTICO]`

### 0.2 Pesquisa de campo (entrevistas)
- [ ] Entrevistar 5+ praticantes experientes sobre acidentes reais que viveram
- [ ] Entrevistar 2+ instrutores/escolas sobre como hoje contam quem está na água
- [ ] Entrevistar 1+ salva-vidas / bombeiro marítimo sobre como recebem um chamado hoje
- [ ] Entrevistar (se possível) Capitania dos Portos / SALVAMAR local sobre formato de acionamento
- [ ] Levantar os 10 cenários de acidente mais comuns (kite despotencializado, linha enrolada, câimbra, prancha perdida, corrente de retorno, vento offshore, colisão, tubarão, hipotermia, pane física)
- [ ] Documentar para cada cenário: tempo típico até alguém perceber, e como o sistema encurtaria isso

### 0.3 Levantamento técnico do spot
- [ ] Medir cobertura celular na água: 500 m / 1 km / 2 km / 5 km da praia (registrar RSRP/RSRQ, operadoras) `[CRÍTICO]`
- [ ] Mapear direção de vento predominante e quando fica offshore
- [ ] Mapear correntes, marés, canais de navegação, pedrais, bancos de areia
- [ ] Mapear pontos de acesso terrestre e por embarcação para resgate
- [ ] Registrar canal VHF local e telefones de emergência (185 / 193 / 192 / salva-vidas do clube)
- [ ] Testar se há ponto elevado para gateway LoRa (torre, prédio, mastro do clube)

### 0.4 Benchmark prático
- [ ] Instalar e usar por 1 semana: Coast Guard SafeTrx (padrão de escalonamento)
- [ ] Instalar e usar: Hoolan / WindsportTracker (padrão de UX esportiva)
- [ ] Subir um Traccar em Docker e testar geofences de círculo e polígono
- [ ] Se possível, testar um inReach Mini 2 ou ZOLEO em sessão real (tempo de fix, autonomia)
- [ ] Escrever relatório "o que copiar / o que evitar" de cada um

### 0.5 Entregáveis da fase
- [ ] Documento de requisitos assinado pelo stakeholder do spot piloto `[CRÍTICO]`
- [ ] Matriz de cenários × detectores
- [ ] Relatório de cobertura do spot com decisão de tecnologia de link

---

## FASE 1 — ARQUITETURA E PROVAS DE CONCEITO

### 1.1 Decisões de arquitetura (ADR — 1 documento por decisão)
- [ ] ADR-01 Link de dados (celular / LoRa / satélite / híbrido)
- [ ] ADR-02 Protocolo de telemetria (MQTT vs HTTP batch) e formato do payload
- [ ] ADR-03 Banco (PostgreSQL+PostGIS+TimescaleDB) e política de retenção
- [ ] ADR-04 Construir do zero vs. usar Traccar como base de ingestão
- [ ] ADR-05 Stack do app (React Native / Flutter / nativo) — decisiva por causa do background location
- [ ] ADR-06 Provedor de SMS/voz e plano de fallback
- [ ] ADR-07 Nuvem, região de dados (Brasil, por LGPD) `[LEGAL]`

### 1.2 Provas de conceito
- [ ] PoC-1: broker MQTT recebendo 100 msg/s com TLS e autenticação por dispositivo
- [ ] PoC-2: PostGIS avaliando 1 ponto contra 50 geofences em < 5 ms
- [ ] PoC-3: app enviando posição em **background** por 4 h com tela apagada, iOS e Android `[CRÍTICO]`
- [ ] PoC-4: buffer offline — modo avião por 30 min e reenvio ordenado sem perda
- [ ] PoC-5: consumo de bateria do celular em 4 h de tracking a 5 s (medir % gasto)
- [ ] PoC-6: SMS e chamada de voz sintetizada chegando com coordenadas legíveis
- [ ] PoC-7: precisão GNSS real dentro d'água salgada com o telefone em bolsa estanque

### 1.3 Entregáveis
- [ ] Diagrama de arquitetura aprovado
- [ ] Esquema de dados versionado (migrations)
- [ ] Definição do contrato de API (OpenAPI) e do payload de telemetria

---

## FASE 2 — BACKEND NÚCLEO

### 2.1 Infraestrutura
- [ ] Repositório, CI/CD, ambientes dev/staging/prod
- [ ] IaC (Terraform) para toda a infra
- [ ] Observabilidade: métricas, logs estruturados, tracing
- [ ] Backup automático do banco + teste de restauração `[CRÍTICO]`
- [ ] Gestão de segredos (nunca em repositório)

### 2.2 Ingestão
- [ ] Endpoint MQTT + REST de ingestão com autenticação por dispositivo `[CRÍTICO]`
- [ ] Validação de esquema e rejeição de payload malformado
- [ ] Deduplicação por (device_id, timestamp)
- [ ] Aceitação de lote offline com marcação `offline_flag`
- [ ] Rate limiting por dispositivo (proteção contra dispositivo defeituoso)
- [ ] Rejeição de posições fisicamente impossíveis (salto > velocidade máxima plausível)

### 2.3 Persistência
- [ ] Hypertable de posições com particionamento por tempo
- [ ] Índices GiST nas geometrias
- [ ] Política de retenção e compressão automática
- [ ] Tabela de auditoria imutável (append-only) para eventos de incidente `[LEGAL]`

### 2.4 Motor de barreiras
- [ ] CRUD de geofences (círculo, polígono, corredor, setor)
- [ ] Avaliação por ponto com estado persistido por (atleta × barreira)
- [ ] Histerese (buffer ~25 m) e debounce (2 fixes) contra ruído de GPS `[CRÍTICO]`
- [ ] Evento de entrada, saída, permanência e **aproximação com rumo**
- [ ] Barreiras dinâmicas: recálculo por vento/maré a cada 5 min
- [ ] Versionamento de geofence (o console de incidente deve mostrar a barreira **vigente na hora do fato**) `[LEGAL]`
- [ ] Barreira pessoal por nível do praticante

### 2.5 API
- [ ] Autenticação (OAuth2/JWT) e RBAC por papel
- [ ] WebSocket de posições ao vivo
- [ ] Endpoints de sessão, incidente, geofence, atleta, spot
- [ ] Rate limit e proteção contra enumeração de usuários
- [ ] Documentação OpenAPI publicada

---

## FASE 3 — MOTOR DE INCIDENTE E ESCALONAMENTO

### 3.1 Detectores `[SAFETY]`
- [ ] D1 Inatividade (vel < 0,5 kt por > 3 min, dentro d'água)
- [ ] D2 Deriva passiva (movimento alinhado à corrente/vento sem propulsão)
- [ ] D3 Saída de Zona Segura / entrada em Zona Proibida
- [ ] D4 Perda de sinal por > N min com última posição na água `[CRÍTICO]`
- [ ] D5 Bateria crítica
- [ ] D6 Impacto / queda brusca (acelerômetro)
- [ ] D7 Botão de pânico (app + físico)
- [ ] D8 ETA do plano de sessão estourado
- [ ] D9 Separação praticante ↔ prancha/kite (se houver tag secundária)
- [ ] D10 Afastamento acelerado da costa acima do esperado
- [ ] Cada detector tem: sensibilidade configurável, teste unitário e registro de por que disparou

### 3.2 Máquina de escalonamento `[SAFETY]` `[CRÍTICO]`
- [ ] N0 Auto-verificação no dispositivo (vibração + som + janela de 60–180 s)
- [ ] N1 Notificação ao buddy
- [ ] N2 Notificação à base/escola/salva-vidas (com sirene no painel)
- [ ] N3 Contatos de emergência (SMS + ligação de voz com coordenadas)
- [ ] N4 Pacote pronto para SAR oficial (SALVAMAR 185 / Bombeiros 193)
- [ ] Timers persistentes (sobrevivem a restart do serviço) `[CRÍTICO]`
- [ ] Idempotência: reinício do serviço não reenvia alertas já enviados
- [ ] Cancelamento autenticado, com registro de autor e motivo
- [ ] Deduplicação de incidentes do mesmo atleta
- [ ] Linha do tempo completa gravada em log imutável

### 3.3 Canais de notificação
- [ ] Push (FCM/APNs) com som crítico que fura o modo silencioso
- [ ] SMS com coordenadas em formato ditável
- [ ] Chamada de voz com TTS repetindo a posição 3×
- [ ] E-mail com mapa estático anexado
- [ ] Webhook para integração com sistema da escola/clube
- [ ] Teste de entrega de cada canal com alarme se o canal cair `[CRÍTICO]`

### 3.4 Testes anti-falso-positivo
- [ ] Simular 100 sessões normais gravadas → contar falsos positivos
- [ ] Simular pausa legítima do praticante (descanso boiando) → não deve escalar além de N0
- [ ] Simular perda de sinal em terra (guardou o celular no carro) → não deve escalar
- [ ] Ajustar limiares e documentar os valores finais

---

## FASE 4 — APLICATIVO DO PRATICANTE

### 4.1 Fluxos essenciais
- [ ] Cadastro + ficha de resgate (foto, cores do equipamento, contatos) `[SAFETY]`
- [ ] Seleção de spot e exibição honesta da cobertura daquele spot `[SAFETY]`
- [ ] Plano de sessão: ETA, buddy, equipamento
- [ ] Check-in (entrar na água) e check-out (sair) com confirmação
- [ ] Tela ao vivo: posição, distância da praia, tempo de sessão, bateria, status do link
- [ ] Botão de pânico grande, acessível com uma mão, com confirmação de 2 s (anti-toque acidental)
- [ ] Resposta ao "Você está bem?" com um toque
- [ ] Feedback de que o socorro foi acionado (confirmação bidirecional) `[SAFETY]`

### 4.2 Robustez técnica
- [ ] Tracking em background aprovado nas duas lojas (permissão "always") `[CRÍTICO]`
- [ ] Fila persistente offline com reenvio ordenado
- [ ] Mapa do spot em cache para uso sem rede
- [ ] Modo economia de bateria automático
- [ ] Reinício automático do tracking após crash do app `[CRÍTICO]`
- [ ] Wake lock / foreground service configurado corretamente no Android
- [ ] Tratamento de revogação de permissão de localização em pleno uso
- [ ] Teste com tela apagada + telefone em bolsa estanque + 4 h reais na água `[CRÍTICO]`

### 4.3 UX de condição real
- [ ] Alto contraste, legível sob sol direto
- [ ] Alvos de toque grandes (mão molhada, dedo enrugado)
- [ ] Sons e vibração distinguíveis do resto do telefone
- [ ] Nenhuma tela que afirme "você está seguro" `[SAFETY]`
- [ ] Onboarding que exige aceite explícito das limitações `[LEGAL]`

### 4.4 Wearables (opcional no MVP)
- [ ] Integração Apple Watch (posição + botão de pânico no pulso)
- [ ] Integração Garmin (Connect IQ)

---

## FASE 5 — PAINEL DE PRAIA E RESCUE CONSOLE

### 5.1 Painel de praia (escola / clube / salva-vidas)
- [ ] Lista de quem está na água agora, com semáforo (verde/amarelo/vermelho)
- [ ] Contador entrou × saiu, com destaque para quem passou do ETA
- [ ] Mapa com todos os atletas e as barreiras vigentes
- [ ] Sirene sonora contínua para alerta N2, silenciável só com reconhecimento
- [ ] Modo TV (tela grande na escola) e modo tablet
- [ ] Funciona em rede instável (reconexão automática de WebSocket)

### 5.2 Rescue Console `[SAFETY]` `[CRÍTICO]`
- [ ] Última posição confiável com **idade do fix** e raio de precisão em destaque
- [ ] Rastro das últimas 2 h
- [ ] Coordenadas em 3 formatos: DD° MM.mmm′ (padrão SAR), decimal, MGRS
- [ ] Hora em UTC e local
- [ ] Ficha do praticante (foto, cores, peso, condição médica)
- [ ] Condições no momento: vento, onda, maré, corrente, temperatura da água
- [ ] Elipse de deriva projetada (15/30/60 min)
- [ ] Botão "copiar pacote SAR" — texto pronto para ditar em rádio
- [ ] Exportar GPX/KML para o GPS da embarcação
- [ ] Modo navegação para o resgatista (rumo + distância, atualizando)
- [ ] Acesso por link temporário seguro para o SAR, com log de acesso `[LEGAL]`
- [ ] Impressão em 1 página para quem vai a campo

---

## FASE 6 — MOTOR DE DERIVA (DATUM DE BUSCA)

- [ ] Integrar fonte de vento e corrente (Open-Meteo Marine / Copernicus / HYCOM)
- [ ] Implementar modelo de leeway para *person-in-water* (coeficientes Allen & Plourde / IAMSAR)
- [ ] Simulação Monte Carlo (N≥1000) com dispersão do erro
- [ ] Gerar datum + elipse de 50 % e 95 % de probabilidade
- [ ] Renderizar mapa de calor no Rescue Console
- [ ] **Validar em campo com boia derivante instrumentada**: soltar, prever, comparar após 30 e 60 min `[CRÍTICO]`
- [ ] Documentar a margem de erro medida e exibi-la na tela (nunca mostrar precisão que não existe) `[SAFETY]`

---

## FASE 7 — HARDWARE DEDICADO (OPCIONAL / PRODUTO)

### 7.1 Definição
- [ ] Escolher módulo: nRF9160 (LTE-M/NB-IoT + GNSS integrado) ou u-blox SARA-R510M8S
- [ ] Definir forma de uso: pulseira, clip no arnês, no colete de impacto ou no capacete
- [ ] Definir se flutua sozinho ou fica preso a item flutuante `[SAFETY]`
- [ ] Definir autonomia alvo (≥ 6 h sessão / ≥ 24 h emergência)

### 7.2 Projeto
- [ ] Esquemático e layout de PCB
- [ ] Antena GNSS e LTE com plano de terra adequado (crítico junto ao corpo e à água salgada)
- [ ] Botão de pânico estanque, acionável com luva
- [ ] Buzzer + LED de estado + vibração
- [ ] Acelerômetro/IMU para detecção de impacto e de imobilidade
- [ ] Carregamento por indução (sem conector exposto ao sal)
- [ ] Caixa IP68, teste de imersão e de queda
- [ ] Teste de corrosão em névoa salina
- [ ] Firmware com OTA seguro e assinado `[CRÍTICO]`
- [ ] Watchdog de hardware e recuperação automática

### 7.3 Certificação
- [ ] Homologação ANATEL `[LEGAL]` `[CRÍTICO]`
- [ ] Ensaios de compatibilidade eletromagnética
- [ ] Certificação de estanqueidade (laudo IP68)
- [ ] Ficha técnica e manual em português

---

## FASE 8 — TESTES E VALIDAÇÃO

### 8.1 Testes de software
- [ ] Cobertura de testes unitários ≥ 80 % no caminho crítico `[CRÍTICO]`
- [ ] Testes de integração fim-a-fim (fix → alerta → console)
- [ ] Teste de carga: 3× o pico previsto, sustentado por 1 h
- [ ] Teste de caos: derrubar broker, banco, serviço de SMS — verificar degradação graciosa `[CRÍTICO]`
- [ ] Teste de restart no meio de um incidente ativo (timers devem sobreviver) `[CRÍTICO]`
- [ ] Teste de relógio: fix com timestamp no futuro/passado
- [ ] Teste de segurança: pentest, OWASP Top 10, teste de autorização por papel `[LEGAL]`

### 8.2 Testes de campo `[SAFETY]` `[CRÍTICO]`
- [ ] Ensaio 1 — sessão normal completa (4 h) sem falso positivo
- [ ] Ensaio 2 — simulação de imobilidade (boiar parado 5 min) → deve abrir N0 e parar lá
- [ ] Ensaio 3 — saída de barreira controlada → deve alertar em < 30 s
- [ ] Ensaio 4 — perda de sinal simulada → deve escalar corretamente
- [ ] Ensaio 5 — acionamento do botão de pânico → cronometrar até N2 e N3
- [ ] Ensaio 6 — **simulado de resgate real com salva-vidas**, do alerta até chegar no alvo, cronometrado `[CRÍTICO]`
- [ ] Ensaio 7 — teste com 10 atletas simultâneos no mesmo spot
- [ ] Ensaio 8 — teste no limite de cobertura celular (distância máxima)
- [ ] Ensaio 9 — teste com bateria baixa e com telefone superaquecido ao sol
- [ ] Relatório de ensaios assinado, com tempos medidos

### 8.3 Validação operacional
- [ ] Protocolo operacional escrito: quem faz o quê em cada nível de alerta `[SAFETY]` `[CRÍTICO]`
- [ ] Treinamento da escola/salva-vidas no painel e no console
- [ ] Simulado periódico agendado (mensal)
- [ ] Canal de suporte durante horário de operação

---

## FASE 9 — CONFORMIDADE LEGAL E PRIVACIDADE `[LEGAL]`

- [ ] Termos de uso com limitação de responsabilidade e aviso de não substituição `[CRÍTICO]`
- [ ] Política de privacidade específica para dados de geolocalização
- [ ] Base legal LGPD definida por finalidade (consentimento + tutela da vida)
- [ ] RIPD (Relatório de Impacto à Proteção de Dados) elaborado
- [ ] DPO/encarregado designado e publicado
- [ ] Consentimento granular: quem vê minha posição (buddy, escola, sempre × só em emergência)
- [ ] Retenção definida (padrão: 90 dias) e exclusão automática
- [ ] Fluxo de exportação e de exclusão de dados a pedido
- [ ] Consentimento parental para menores
- [ ] Registro de todos os acessos ao Rescue Console
- [ ] Seguro de responsabilidade civil contratado
- [ ] Acordo formal (ou pelo menos ciência documentada) com o clube/escola sobre o papel de cada parte
- [ ] Consulta à Capitania dos Portos sobre o uso pretendido

---

## FASE 10 — PILOTO CONTROLADO

- [ ] 1 spot, 20–50 praticantes voluntários, 4–8 semanas
- [ ] Termo de participação assinado `[LEGAL]`
- [ ] Coleta diária de métricas: falsos positivos, cobertura de fix, bateria, latência
- [ ] Pesquisa semanal de percepção com praticantes e salva-vidas
- [ ] Pós-mortem escrito de **todo** incidente, real ou falso `[SAFETY]`
- [ ] Critérios de aprovação do piloto definidos ANTES de começar `[CRÍTICO]`
- [ ] Decisão go/no-go documentada

---

## FASE 11 — OPERAÇÃO CONTÍNUA

- [ ] SLOs monitorados com alarme (latência, disponibilidade do caminho crítico)
- [ ] "Dead man's switch": alarme quando o próprio sistema perde a capacidade de alertar `[CRÍTICO]`
- [ ] Plantão definido para horário de operação do spot
- [ ] Runbook de incidente de plataforma
- [ ] Revisão trimestral dos limiares dos detectores com dados reais
- [ ] Atualização das barreiras quando o spot mudar (banco de areia, obra, nova área de navegação)
- [ ] Roadmap de expansão: novos spots, satélite, hardware dedicado, integração formal com SAR

---

## CHECKLIST DE "NUNCA" — regras que não se negociam `[SAFETY]`

- [ ] Nunca exibir coordenada sem hora e sem raio de precisão
- [ ] Nunca tratar última posição conhecida como posição atual
- [ ] Nunca prometer resgate; o sistema **avisa**, não salva
- [ ] Nunca deixar o caminho de emergência depender de componente não essencial
- [ ] Nunca lançar alteração no caminho crítico sem ensaio de campo
- [ ] Nunca desabilitar um alerta sem registrar quem, quando e por quê
- [ ] Nunca vender, compartilhar ou monetizar dados de localização
- [ ] Nunca substituir o acionamento oficial (185/193) — sempre facilitá-lo
