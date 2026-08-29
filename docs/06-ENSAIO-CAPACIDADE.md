# Ensaio 2 — Capacidade do gateway LoRa

**O que este ensaio decide:** quantos praticantes um gateway sustenta **sem sacrificar o mais distante** — e qual configuração de rede empurra esse limite.
**Duração:** duas meias-diárias na praia. **Não precisa de barco.**
**Data:** 2026-08-28

---

## 1. A pergunta certa

O levantamento de tecnologias produziu uma tabela de capacidade a partir do tempo de ar: SF7 sustentaria 233 praticantes a cada 10 s, SF12 apenas 10. Essa conta assume ALOHA puro e trata todos os nós como iguais.

**Eles não são iguais, e é aí que mora o problema.**

Numa colisão entre dois pacotes no mesmo canal e mesmo SF, sobrevive o mais forte — é o efeito de captura, e ele precisa de cerca de 6 dB de diferença. Os nós fortes são os que estão perto da praia. O nó fraco é o praticante distante, derivando. E ele acumula as duas piores propriedades ao mesmo tempo:

| | Praticante perto da praia | Praticante no limite do alcance |
|---|---|---|
| Fator de espalhamento | SF7 | SF12 |
| Tempo de ar por pacote | **62 ms** | **1483 ms** — 24× mais |
| Potência recebida | forte | no limiar da sensibilidade |
| Numa colisão | vence | **perde sempre** |
| Risco real | baixo, está na beira | **alto, é por ele que o sistema existe** |

O pacote que fica 1,5 s no ar é exposto a muito mais sobreposição, e quando ela acontece ele perde. **A taxa de entrega média pode ficar em 91% enquanto o praticante que mais precisa ser ouvido está em 13%.**

Por isso este ensaio não mede a média. Ele mede a taxa de entrega **por classe de distância** e a do **pior nó**.

---

## 2. O que o simulado já mostra

Antes de comprar equipamento, rodei `simular_capacidade.py` com o modelo de colisão, captura e limite de demoduladores. Os números abaixo **são simulação, não medição** — o ensaio existe justamente para medi-los. O que eles estabelecem é o formato do problema e o desenho necessário do ensaio.

Configuração de referência: todos os nós a cada 10 s, 8 canais compartilhados, rodadas de 30 min.

| Nós | Carga por canal | Entrega agregada | Classe "limite" (SF12, longe) |
|---|---|---|---|
| 10 | 0,036 erlang | 98,2% | **100%** |
| 20 | 0,076 | 96,8% | **90,6%** |
| 30 | 0,097 | 95,5% | **85,1%** |
| 45 | 0,139 | 91,5% | **43,3%** |
| 60 | 0,229 | 84,5% | **13,0%** |

A média cai devagar; a classe crítica desaba. Com 45 nós, o sistema parece funcionar a 91,5% e o praticante mais distante já perde metade dos pacotes.

**O índice de Jain não detecta isso.** Ele ficou em 0,99 durante todo o colapso, porque a minoria prejudicada é pequena demais para mover a métrica. Registro aqui para quem for revisar o método: **justiça agregada é a métrica errada para este problema.** O que serve é a taxa por classe e a do pior nó.

---

## 3. Hipóteses

Escritas antes da medição:

| Hipótese | Previsão | Derrubada se |
|---|---|---|
| H1 — capacidade da configuração de referência | 20 a 30 praticantes a cada 10 s com o pior nó ≥ 90% | menos de 12 |
| H2 — a média esconde a falha | diferença > 15 pontos entre agregada e classe "limite" antes do colapso | diferença < 5 pontos |
| H3 — taxa por classe ajuda | taxa adaptativa por distância eleva a capacidade em ≥ 50% | ganho < 20% |
| H4 — o alerta de emergência passa | pacote de emergência entregue em ≥ 99% das tentativas com a rede em carga máxima | abaixo de 95% |

**H4 é a hipótese que mais importa.** Todo o resto é conforto; essa é a função do sistema.

---

## 4. Desenho do ensaio

### 4.1 Por que na praia, e não na água

A variável que interessa não é a distância — é a **diferença de potência recebida** entre os nós. Isso se emula melhor com atenuadores calibrados do que com barco: é repetível, barato e permite refazer a mesma rodada quantas vezes for preciso.

Vinte nós numa mesa na praia, cada um com atenuação fixa escolhida para reproduzir a potência que teria a 1, 6, 14 e 22 km, entregam um ensaio muito mais limpo que vinte pessoas na água.

**Uma verificação cruzada, porém, é obrigatória:** um nó real na água, a distância real, durante uma rodada — para confirmar que a emulação por atenuador reproduz o que o mar faz. Aproveitar o dia de barco do Ensaio 1 para isso.

### 4.2 Classes emuladas

| Classe | Distância emulada | SF | Atenuação sobre o nó de referência | Proporção dos nós |
|---|---|---|---|---|
| perto | 1 km | SF7 | 0 dB | 45% |
| médio | 6 km | SF9 | 30 dB | 30% |
| longe | 14 km | SF10 | 45 dB | 18% |
| **limite** | 22 km | SF12 | **53 dB** | 7% |

A atenuação sai do modelo de dois raios já validado: 40·log₁₀(d) com o gateway a 30 m. Conferir com o RSSI que o gateway reporta em cada nó antes de começar — **se o RSSI medido não bater com o previsto em ±3 dB, ajustar o atenuador até bater.** A emulação vale pelo RSSI, não pelo valor nominal do atenuador.

### 4.3 As quatro configurações a testar

| Config | O que muda | O que testa |
|---|---|---|
| **A — referência** | Todos a cada 10 s, 8 canais compartilhados | O ponto de partida e a hipótese H1 |
| **B — taxa por classe** | perto 30 s, médio 20 s, longe 10 s, limite 10 s | H3. Quem está na beira não precisa de atualização de 10 em 10 s; quem está longe precisa |
| **C — B + canais reservados** | 2 dos 8 canais exclusivos para SF11 e SF12 | Separar o fraco da disputa com o forte |
| **D — emergência sob carga** | Rede em carga máxima, um nó entra em modo de emergência: SF12, a cada 2 s | **H4.** É o único teste que mede a função de segurança |

> **Um resultado do simulado que vale carregar para o campo:** reservar **um** canal para SF11/SF12 piorou tudo — concentra os nós lentos num canal só e eles passam a colidir entre si. Com **dois** canais o resultado melhorou. A configuração C existe por causa disso; testar a variante de um canal só é desperdício de rodada.

### 4.4 Quantos nós por rodada

Níveis de 10, 20, 30, 45 e 60 nós. Com 20 nós físicos, os níveis acima de 20 se obtêm fazendo cada nó gerar o tráfego de dois ou três nós virtuais — mesmo tempo de ar, identificadores distintos. O que o canal enxerga é idêntico; o que muda é que a diversidade espacial fica menor, e isso deve ser anotado no relatório.

### 4.5 Duração de cada rodada — a conta que define o dia

Uma taxa de entrega estimada em cima de poucas dezenas de pacotes é ruído. Para decidir se um nó está acima ou abaixo de 90% com ±5 pontos e 95% de confiança:

```
n = 1,96² × 0,9 × 0,1 / 0,05²  ≈  138 pacotes
```

A 10 s por pacote, são **23 minutos de rodada** — arredondando, **25 minutos**. A análise calcula esse mínimo sozinha e avisa quando a rodada foi curta demais para concluir.

Isso não é preciosismo: na primeira versão deste ensaio, rodadas de 10 minutos indicaram capacidade de 27 praticantes; com rodadas de 30 minutos, a mesma configuração entregou 10. **A rodada curta superestimou a capacidade em 2,7 vezes.**

### 4.6 Cronograma

| Meia-diária | Rodadas | Tempo |
|---|---|---|
| **Tarde 1** | Config A nos 5 níveis | 5 × 25 min + trocas ≈ 2h45 |
| **Manhã 2** | Config B (3 níveis), Config C (3 níveis) | 6 × 25 min + trocas ≈ 3h15 |
| **Manhã 2, final** | Config D — emergência sob carga, 3 repetições no nível mais alto | 45 min |

Antes de qualquer rodada: conferência de RSSI de todos os nós contra o previsto, e 10 minutos de gateway ouvindo sem nenhum nó ligado, para medir o ruído de fundo.

---

## 5. Equipamento

Assume que o gateway, a antena, o mastro e três nós já existem do Ensaio 1.

| Item | Qtd | Especificação | R$ (un.) | R$ |
|---|---|---|---|---|
| Nós adicionais | 17 | Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262). **Sem GNSS** — a posição é fixa e conhecida | 220 | 3.740 |
| Atenuadores SMA fixos | 12 | jogo de 10, 20 e 30 dB, 2 W, DC–3 GHz | 70 | 840 |
| Cabos SMA curtos | 12 | 15 cm, macho-fêmea | 25 | 300 |
| Hub USB alimentado | 2 | 10 portas, 3 A — alimenta e coleta os logs por serial | 150 | 300 |
| Extensão e fonte | 1 | régua, cabos, ou gerador pequeno se não houver energia | 400 | 400 |
| RTL-SDR | 1 | conferir ocupação do canal e ruído de fundo — separa colisão de interferência | 300 | 300 |
| Caixa organizadora | 2 | transporte e bancada de campo | 100 | 200 |
| Toldo ou tenda | 1 | notebook e bancada ao sol não duram a tarde | 350 | 350 |
| **Total adicional** | | | | **R$ 6.230** |

Já existentes do Ensaio 1: gateway, antena, cabo, mastro, alimentação, 3 nós com GNSS, notebook.

### 5.1 Coleta dos logs

Os nós de bancada não precisam de cartão SD: ficam ligados por USB ao notebook e imprimem cada transmissão na serial. Um coletor de ~20 linhas com `pyserial` escreve o `nos.csv` no formato que a análise espera. Alternativa sem dependência nenhuma: reaproveitar o firmware do Ensaio 1, que grava em cartão, e juntar os arquivos no fim.

**Contrato dos arquivos** — a análise não aceita outro formato:

```
nos.csv      rodada,t_s,no_id,seq,sf,canal,classe,intervalo_s
gateway.csv  rodada,t_s,no_id,seq,sf,canal,rssi_dbm,snr_db
```

---

## 6. Métricas e regra de decisão

Para cada rodada, a análise reporta:

- **Carga oferecida por canal**, em erlangs
- **Taxa de entrega agregada** — informativa, nunca decisória
- **Taxa por classe de distância**, com intervalo de confiança de Wilson
- **Taxa do pior nó**, com intervalo de confiança
- **Índice de Jain** — registrado, mas sabidamente insensível a este modo de falha

**A regra de decisão usa o limite inferior do intervalo de confiança do pior nó**, não o valor pontual:

| Situação | Veredito |
|---|---|
| Limite inferior ≥ 90% | passa |
| Limite superior < 90% | reprova |
| O intervalo cruza os 90% | **indefinido — rodada mais longa**, não é um empate a favor |

A terceira linha existe para impedir que uma rodada curta seja lida como aprovação.

---

## 7. O que fazer com o resultado

| Capacidade medida na config A | Leitura | Ação |
|---|---|---|
| **≥ 30 praticantes** | Folgado para qualquer spot brasileiro | Seguir com a configuração simples |
| **15 a 30** | Suficiente para a maioria dos picos | Adotar a config B ou C conforme o ganho medido |
| **8 a 15** | Aperta em dia de vento bom no Cumbuco | Config C obrigatória; considerar segundo gateway |
| **< 8** | Inviável como camada primária de um pico movimentado | Reabrir a arquitetura: mais gateways, outra banda, ou celular como primário |

E, independente do número: **se H4 falhar — se o alerta de emergência não passar com a rede em carga — nenhuma outra configuração importa.** O sistema precisa de um mecanismo de prioridade real, e isso vira requisito antes de qualquer piloto.

---

## 8. Riscos do ensaio

| Risco | Consequência | Prevenção |
|---|---|---|
| Atenuação não confere com o RSSI previsto | A emulação não representa o mar | Conferência de RSSI nó a nó antes de cada configuração; ajustar até bater em ±3 dB |
| Rodada curta demais | Superestima a capacidade em até 2,7× | 25 min por rodada; a análise avisa quando a amostra é insuficiente |
| Acoplamento direto entre nós na mesa | Colisões que não existiriam no mar | Espaçar os nós, usar atenuador em cada um, conferir com o RTL-SDR |
| Interferência local confundida com colisão | Diagnóstico errado | 10 min de gateway ouvindo sem nós ligados, no início |
| Nós virtuais mal implementados | Carga irreal | Conferir o tempo de ar total contra o previsto pela fórmula |
| Notebook desliga no meio | Perde a rodada | Toldo, fonte externa, gravação incremental em disco |

---

## 9. Entregáveis

1. `nos.csv` e `gateway.csv` brutos de cada rodada, arquivados sem edição
2. `capacidade_resultado.csv` com carga, entrega agregada, entrega do pior nó e intervalos
3. Curva de entrega por classe de distância contra número de nós, para as configs A, B e C
4. Resposta a H4 com as três repetições
5. Recomendação de configuração para o piloto: intervalos por classe, reserva de canais e mecanismo de prioridade em emergência
6. Se a capacidade medida for muito diferente da prevista, a tabela de capacidade do levantamento de tecnologias corrigida

---

## 10. Ferramentas

Em `tools/ensaio-lora/`:

```bash
# ensaio seco: dimensiona o ensaio e treina a leitura do relatorio
python3 simular_capacidade.py --saida-dir /tmp/cap --duracao-s 1800 --nos 10 20 30 45 60
python3 analisar_capacidade.py --nos /tmp/cap/nos.csv --gateway /tmp/cap/gateway.csv

# variantes de configuracao
python3 simular_capacidade.py --saida-dir /tmp/capB --intervalo-por-classe 30 20 10 10
python3 simular_capacidade.py --saida-dir /tmp/capC --intervalo-por-classe 30 20 10 10 --canais-lentos 2

# com os dados reais, trocar os CSV
python3 analisar_capacidade.py --nos nos.csv --gateway gateway.csv --pdr-alvo 0.9
```
