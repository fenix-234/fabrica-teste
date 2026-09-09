#!/usr/bin/env bash
# rastrear_porta.sh — Rastreia um evento "porta passou a escutar em qualquer interface".
#
# SOMENTE LEITURA: este script apenas coleta evidências. Ele nao altera
# configuracao, nao para servicos e nao mexe em firewall.
#
# Uso:
#   sudo ./scripts/rastrear_porta.sh [PORTA] [HORA_INICIO] [HORA_FIM]
# Exemplo (o evento das 04:51 na porta 9100):
#   sudo ./scripts/rastrear_porta.sh 9100 04:40 05:10
#
# Rode com sudo: sem root, o sistema esconde o nome do processo dono da porta.

set -uo pipefail

PORTA="${1:-9100}"
INI="${2:-04:40}"
FIM="${3:-05:10}"

tem() { command -v "$1" >/dev/null 2>&1; }
secao() { printf '\n\n===== %s =====\n' "$1"; }

printf 'RASTREIO DE PORTA — relatorio\n'
printf 'porta.....: %s\n' "$PORTA"
printf 'janela....: %s a %s\n' "$INI" "$FIM"
printf 'maquina...: %s\n' "$(hostname 2>/dev/null)"
printf 'gerado em.: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
printf 'usuario...: %s' "$(id -un 2>/dev/null)"
[ "$(id -u)" -ne 0 ] && printf '  <<< SEM ROOT: rode com sudo para ver o dono da porta'
printf '\n'

# ---------------------------------------------------------------- 1. quem escuta
secao "1. QUEM ESTA ESCUTANDO NA PORTA $PORTA (agora)"
LINHAS=""
if tem ss; then
  LINHAS="$(ss -tulpnH 2>/dev/null | grep -E "[:.]${PORTA}([^0-9]|$)")"
elif tem netstat; then
  LINHAS="$(netstat -tulpn 2>/dev/null | grep -E "[:.]${PORTA}([^0-9]|$)")"
else
  echo "AVISO: nem 'ss' nem 'netstat' encontrados (instale: apt install iproute2)."
fi

if [ -z "$LINHAS" ]; then
  echo "Nada escutando na porta $PORTA neste momento."
  echo "=> Se o alerta foi das $INI, o servico pode ja ter sido encerrado."
else
  echo "$LINHAS"
  if echo "$LINHAS" | grep -qE '(^|[^0-9.])(0\.0\.0\.0|\*|\[::\]):'"$PORTA"; then
    echo
    echo ">>> CONFIRMADO: escutando em TODAS as interfaces (0.0.0.0 ou [::])."
    echo ">>> Qualquer maquina que alcance este host pode conectar nesta porta."
  else
    echo
    echo ">>> Escutando apenas em endereco especifico (nao e 0.0.0.0)."
    echo ">>> A exposicao pode ja ter sido corrigida desde o alerta."
  fi
fi

# ------------------------------------------------------- 2. identidade do processo
secao "2. PROCESSO DONO DA PORTA"
PIDS="$(printf '%s\n' "$LINHAS" | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)"
[ -z "$PIDS" ] && PIDS="$(printf '%s\n' "$LINHAS" | grep -oE '[0-9]+/' | tr -d '/' | sort -u)"

if [ -z "$PIDS" ]; then
  echo "Nenhum PID identificado (falta root, ou nada escutando)."
else
  for p in $PIDS; do
    [ -d "/proc/$p" ] || continue
    echo "--- PID $p ---"
    ps -o pid,ppid,user,lstart,etime,cmd -p "$p" 2>/dev/null
    echo "binario : $(readlink -f "/proc/$p/exe" 2>/dev/null || echo '(sem permissao)')"
    echo "cgroup  : $(tr -d '\0' < "/proc/$p/cgroup" 2>/dev/null | head -1)"
    if tem systemctl; then
      UNIT="$(systemctl status "$p" 2>/dev/null | head -1)"
      [ -n "$UNIT" ] && echo "unidade : $UNIT"
    fi
    BIN="$(readlink -f "/proc/$p/exe" 2>/dev/null)"
    if [ -n "$BIN" ] && tem dpkg; then
      echo "pacote  : $(dpkg -S "$BIN" 2>/dev/null || echo '(nao pertence a pacote .deb — binario avulso)')"
    fi
    echo
  done
fi

# ------------------------------------------------------------------- 3. containers
secao "3. CONTAINERS (causa mais comum de bind em 0.0.0.0)"
if tem docker && docker info >/dev/null 2>&1; then
  echo "-- containers rodando e portas publicadas --"
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.RunningFor}}\t{{.Ports}}' 2>/dev/null
  echo
  echo "-- containers que publicam a porta $PORTA --"
  docker ps -a --format '{{.Names}}\t{{.Ports}}' 2>/dev/null | grep -E "[:.]${PORTA}(->|/|[^0-9]|$)" \
    || echo "(nenhum)"
  echo
  echo "NOTA: 'docker run -p 9100:9100' publica em 0.0.0.0 e ignora o UFW."
  echo "      Para restringir ao proprio host use '-p 127.0.0.1:9100:9100'."
else
  echo "Docker nao instalado ou sem permissao de acesso."
fi
if tem podman; then
  echo; echo "-- podman --"; podman ps --format 'table {{.Names}}\t{{.Ports}}' 2>/dev/null
fi

# ------------------------------------------------------------------------ 4. logs
secao "4. O QUE ACONTECEU ENTRE $INI E $FIM"
if tem journalctl; then
  HOJE="$(date '+%Y-%m-%d')"
  echo "--- log do sistema na janela do evento ---"
  journalctl --since "$HOJE $INI" --until "$HOJE $FIM" --no-pager 2>/dev/null | tail -80 \
    || echo "(sem acesso ao journal — use sudo)"
  echo
  echo "--- servicos iniciados/reiniciados nessa janela ---"
  journalctl --since "$HOJE $INI" --until "$HOJE $FIM" --no-pager 2>/dev/null \
    | grep -iE "started|starting|reload|restart|iniciad" | tail -40 || echo "(nada)"
  echo
  echo "--- atualizacoes automaticas (04:00-06:00 e a janela tipica) ---"
  journalctl -u unattended-upgrades -u apt-daily -u apt-daily-upgrade \
    --since "$HOJE $INI" --until "$HOJE $FIM" --no-pager 2>/dev/null | tail -30 || echo "(nada)"
else
  echo "journalctl indisponivel; tentando /var/log/syslog"
  grep -E "^[A-Za-z]{3} +[0-9]+ ${INI%%:*}:" /var/log/syslog 2>/dev/null | tail -40 \
    || echo "(sem syslog legivel)"
fi

echo
echo "--- pacotes instalados/atualizados hoje (apt) ---"
grep "$(date '+%Y-%m-%d')" /var/log/dpkg.log 2>/dev/null | grep -E ' (install|upgrade) ' | tail -25 \
  || echo "(nenhum ou sem acesso a /var/log/dpkg.log)"

# ------------------------------------------------------------- 5. acesso e config
secao "5. QUEM ACESSOU A MAQUINA / O QUE MUDOU"
echo "--- ultimos logins ---"
last -n 15 2>/dev/null || echo "(indisponivel)"
echo
echo "--- autenticacoes na janela do evento ---"
if tem journalctl; then
  journalctl -u ssh -u sshd --since "$(date '+%Y-%m-%d') $INI" --until "$(date '+%Y-%m-%d') $FIM" \
    --no-pager 2>/dev/null | tail -30 || echo "(nada)"
else
  grep -E "$(date '+%b %e')" /var/log/auth.log 2>/dev/null | tail -30 || echo "(nada)"
fi
echo
echo "--- arquivos de configuracao alterados nas ultimas 24h ---"
find /etc /opt -xdev -type f -mtime -1 2>/dev/null | grep -vE '/etc/(mtab|resolv.conf)$' | head -40 \
  || echo "(nenhum)"

# --------------------------------------------------------------------- 6. firewall
secao "6. FIREWALL — a porta esta realmente alcancavel?"
if tem ufw; then
  echo "--- ufw ---"; ufw status verbose 2>/dev/null || echo "(precisa de root)"
fi
if tem firewall-cmd; then
  echo "--- firewalld ---"; firewall-cmd --list-all 2>/dev/null
fi
if tem nft; then
  echo "--- nftables (regras citando a porta) ---"
  nft list ruleset 2>/dev/null | grep -E "(dport|sport) *$PORTA" || echo "(nenhuma regra especifica)"
fi
if tem iptables; then
  echo "--- iptables INPUT ---"; iptables -L INPUT -n --line-numbers 2>/dev/null | head -25
fi

# ------------------------------------------------------------- 7. alcance na rede
secao "7. ALCANCE NA REDE"
echo "--- enderecos desta maquina ---"
ip -4 -o addr show 2>/dev/null | awk '{print "  " $2 "  " $4}' || echo "(indisponivel)"
echo
echo "--- rota padrao (o roteador) ---"
ip route show default 2>/dev/null || echo "(indisponivel)"
echo
echo "VERIFICACAO MANUAL IMPORTANTE (nenhum comando faz isso por voce):"
echo "  Entre no roteador acima e confirme que NAO existe redirecionamento"
echo "  de porta (port forwarding / DMZ / UPnP) apontando para a porta $PORTA."
echo "  Rede interna = risco moderado. Exposto na internet = risco alto e urgente."

secao "FIM DO RELATORIO"
echo "Este script nao alterou nada no sistema."
