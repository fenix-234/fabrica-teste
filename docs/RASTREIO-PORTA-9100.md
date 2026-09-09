# Rastreio — "Porta 9100 passou a escutar em qualquer interface"

Registro do evento 🟠 do painel VIGIA (`http://192.168.1.37:9000/seguranca`),
detectado às **04:51**, e o procedimento para rastreá-lo.

## O que o alerta significa

Todo programa que atende pela rede escuta numa **porta** (um número de canal).
A porta pode escutar de dois jeitos:

| Modo | Analogia | Quem alcança |
|---|---|---|
| `127.0.0.1` (local) | Porta interna, dentro da sala | Só a própria máquina |
| `0.0.0.0` (qualquer interface) | Porta da frente, para a rua | Qualquer aparelho da rede — e a internet, se o roteador redirecionar |

O alerta diz que algo **antes fechado passou a estar aberto para a rede**.
É 🟠 laranja porque é um *aumento de exposição*, não prova de invasão.

## O que costuma usar a porta 9100

1. **Impressão direta (RAW / JetDirect)** — porta padrão de impressoras de rede,
   etiquetadoras e plotters. Comum em serralheria (etiqueta de peça, ordem de
   corte). Risco: a 9100 de impressão **não tem autenticação nenhuma** — qualquer
   um na rede manda imprimir o que quiser.
2. **`node_exporter` (Prometheus)** — agente de monitoramento, 9100 por padrão.
   Risco: expõe dados da máquina (memória, discos, processos) a quem perguntar.

Descobrir **qual dos dois** é o primeiro passo do rastreio — o script faz isso.

## Como rastrear

Na máquina `192.168.1.37`:

```bash
sudo ./scripts/rastrear_porta.sh 9100 04:40 05:10
```

O script é **somente leitura**: coleta evidências, não altera configuração, não
para serviços, não mexe no firewall. Ele responde, em sete seções:

1. **Quem escuta** na 9100 agora, e se é mesmo `0.0.0.0`
2. **Qual processo** é o dono — binário, usuário, de que pacote veio
3. **Containers** — `docker run -p 9100:9100` publica em `0.0.0.0` e **ignora o
   UFW**; é a causa mais comum desse alerta
4. **O que aconteceu na janela do evento** — serviços reiniciados, atualizações
   automáticas (04:00–06:00 é a janela típica do `unattended-upgrades`, o que
   combina com as 04:51)
5. **Quem acessou** a máquina e que arquivos de config mudaram nas últimas 24h
6. **Firewall** — se a porta está de fato alcançável
7. **Alcance na rede** — endereços e o roteador a conferir

Guarde a saída para comparar com o próximo alerta:

```bash
sudo ./scripts/rastrear_porta.sh 9100 04:40 05:10 > rastreio-9100.txt 2>&1
```

## Hipótese principal

O horário **04:51** cai na janela de manutenção automática do Linux
(`apt-daily-upgrade` / `unattended-upgrades`, tipicamente entre 04:00 e 06:00).
Uma atualização que reinicia um serviço pode restaurar o padrão do pacote —
e vários pacotes trazem `0.0.0.0` como padrão de fábrica.

Se a seção 4 do relatório mostrar uma atualização nessa janela, essa é a causa,
e a correção é **fixar o endereço de escuta na configuração** (não só reiniciar
o serviço), para que a próxima atualização não desfaça o ajuste de novo.

## O passo que nenhum comando faz por você

Entre no roteador e confirme que **não existe redirecionamento de porta**
(port forwarding / DMZ / UPnP) apontando para a 9100.

- Só rede interna da fábrica → risco moderado.
- Alcançável pela internet → **risco alto, feche agora**.

## Nota do repositório `fenix`

O repositório do rig de mineração (`fenix-234/fenix`) **não usa a porta 9100**.
Suas APIs são 4067 (T-Rex), 4068 (lolMiner) e 5000 (Rigel), todas fixadas em
`127.0.0.1`. O `docs/seguranca.md` de lá já alerta contra expor essas APIs em
`0.0.0.0`. Ou seja: **este evento não vem do rig** — mas vale conferir aquelas
três portas na mesma varredura, trocando o primeiro argumento do script.
