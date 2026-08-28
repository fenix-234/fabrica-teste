# Pendente: implantar o formulário na Central Fênix

O arquivo `faturamento-direto.html` está pronto e testado. Falta só copiar para o
servidor — a Central roda na rede privada Tailscale (`desktop-pu30cah…:9443`,
`192.168.1.37:9000`), fora do alcance das sessões na nuvem, então a instalação
tem que sair de dentro da própria máquina.

Enquanto não implanta, o formulário funciona por aqui:
https://claude.ai/code/artifact/f935c132-4112-4946-a289-36b1b9785ef6

## Passo 1 — baixar o arquivo no servidor

Windows (PowerShell):

```powershell
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/fenix-234/fabrica-teste/claude/grupo-mateus-billing-email-530g3c/central-fenix/faturamento-direto.html" `
  -OutFile "$HOME\faturamento-direto.html"
```

Linux:

```bash
curl -fsSL -o ~/faturamento-direto.html \
  https://raw.githubusercontent.com/fenix-234/fabrica-teste/claude/grupo-mateus-billing-email-530g3c/central-fenix/faturamento-direto.html
```

## Passo 2 — descobrir onde a Central serve as páginas

Windows:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 9443,9000 |
  Select-Object LocalPort, OwningProcess,
    @{n='Programa';e={(Get-Process -Id $_.OwningProcess).Path}}
docker ps --format "{{.Names}}  {{.Image}}  {{.Ports}}"
```

Linux:

```bash
sudo ss -lptn 'sport = :9443 or sport = :9000'
docker ps --format '{{.Names}}  {{.Image}}  {{.Ports}}'
```

## Passo 3 — instalar

Mover o arquivo para a pasta de páginas estáticas da Central e criar o item no
menu, no mesmo padrão de `/backup`. Se a Central for container, montar por volume
em vez de copiar — assim a página se atualiza a cada push no repositório.

É HTML autocontido: sem build, sem dependência externa, sem backend.

## O que trazer para a próxima sessão

A saída do Passo 2 — com ela dá para escrever o patch completo (caminho do
arquivo, rota e item de menu) de uma vez.
