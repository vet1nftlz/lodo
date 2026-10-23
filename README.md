# DreamTeam Bot

Bot de Discord estilo DreamTeam: economia em Robux, elenco de jogadores, escalação em 4v4/7v7 e batalhas com aposta.

## 📁 Estrutura do projeto

```
dreamteam_bot/
├── main.py              # ponto de entrada, liga tudo
├── config.py            # constantes (economia, formações, cores)
├── database.py          # acesso ao SQLite (aiosqlite)
├── players_data.py      # catálogo de jogadores da loja
├── cards.py             # monta o card visual (embed + imagem) de um jogador
├── gacha_logic.py       # lógica de abertura de pacotes (compartilhada)
├── maquina.py           # gera o time da CPU pros campeonatos
├── motor_partida.py     # narração ao vivo (converte eventos simulados em texto e revela aos poucos)
├── simulador_partida.py # simulação de verdade: ratings, controle da partida, placar emergente
├── requirements.txt     # dependências
├── .env.example         # exemplo de variável de ambiente (token)
├── assets/cards/        # imagens das cartas dos jogadores
└── cogs/
    ├── economia.py       # /saldo /salario /diario /pagar
    ├── loja.py            # /loja (só pacotes) /inventario
    ├── claim.py           # /claim
    ├── weekly.py          # /weekly
    ├── vender.py          # /vender
    ├── trade.py           # /trade
    ├── info.py            # /info (só cartas que você possui)
    ├── time.py            # /time_montar /time_ver /time_remover
    ├── batalha.py         # /batalha
    ├── amistoso.py        # /amistoso (era /campeonato)
    └── campeonato.py      # /campeonato (torneio: quartas -> semis -> final)
```

## 🔧 Passo a passo para ligar o bot ao seu Discord

### 1. Criar a aplicação e pegar o token (se ainda não tem)

1. Acesse https://discord.com/developers/applications
2. Clique em **New Application**, dê um nome (ex: DreamTeam)
3. No menu lateral, vá em **Bot** → **Reset Token** (ou **Add Bot** se ainda não existir) → copie o token
   - **Nunca compartilhe esse token.** Quem tiver ele controla seu bot.

### 2. Ativar os Intents necessários

Ainda na aba **Bot**, role até **Privileged Gateway Intents** e ative:
- ✅ **Message Content Intent**

(Os comandos aqui são todos slash commands, então isso é opcional, mas deixa ativado por segurança/uso futuro.)

### 3. Convidar o bot para o seu servidor

1. Vá em **OAuth2 → URL Generator**
2. Em **Scopes**, marque: `bot` e `applications.commands`
3. Em **Bot Permissions**, marque pelo menos:
   - Send Messages
   - Embed Links
   - Use Slash Commands
   - Read Message History
4. Copie a URL gerada no final da página, cole no navegador e escolha seu servidor

### 4. Configurar o projeto localmente

1. Instale o Python 3.10+ se ainda não tiver
2. Extraia os arquivos deste projeto em uma pasta
3. Abra um terminal nessa pasta e crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```
4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
5. Renomeie `.env.example` para `.env` e cole seu token:
   ```
   DISCORD_TOKEN=seu_token_aqui
   ```

### 5. Rodar o bot

```bash
python main.py
```

Se tudo estiver certo, você verá algo como:
```
📦 Cog carregado: cogs.economia
📦 Cog carregado: cogs.loja
📦 Cog carregado: cogs.gacha
📦 Cog carregado: cogs.claim
📦 Cog carregado: cogs.weekly
📦 Cog carregado: cogs.vender
📦 Cog carregado: cogs.trade
📦 Cog carregado: cogs.info
📦 Cog carregado: cogs.time
📦 Cog carregado: cogs.batalha
📦 Cog carregado: cogs.amistoso
📦 Cog carregado: cogs.campeonato
✅ Bot conectado como DreamTeam#1234 (ID: ...)
🔄 X slash commands sincronizados.
```

5. (Opcional, mas recomendado) Pra os comandos aparecerem **na hora** durante testes, em vez de esperar até 1h:
   - Ative o **Modo Desenvolvedor** no Discord (Configurações → Avançado)
   - Clique com o botão direito no ícone do seu servidor de testes → **Copiar ID do Servidor**
   - No Railway (ou no `.env` local), adicione:
     ```
     GUILD_ID=id_do_seu_servidor
     ```
   - Reinicie o bot. Os comandos aparecem em segundos nesse servidor específico.

## 🎮 Comandos disponíveis

### Economia
- `/saldo [jogador]` — vê seu saldo ou o de outra pessoa
- `/salario` — ganha 10 a 20 Robux (cooldown de 5 minutos) *(era `/trabalhar`)*
- `/diario` — resgata 20 Robux (cooldown de 24h)
- `/pagar jogador quantidade` — transfere Robux para outro jogador

### Loja e elenco
- `/loja` — mostra os pacotes disponíveis (sem revelar a lista de jogadores — o mistério de descobrir as cartas é a graça da coisa) e a opção de expandir o inventário. Botões pra fazer tudo direto ali.
- `/claim` — carta grátis a cada **20 minutos**, sorteada entre as 27 cartas do catálogo
- `/weekly` — pacote semanal (cooldown de **7 dias**), com 3 cartas reveladas em suspense uma por uma
- `/info nome` — mostra a carta completa (imagem + overall + raridade) de um jogador **que você já possui**. Tem autocomplete, mas só sugere nomes do seu próprio elenco — cartas que você ainda não pegou continuam em mistério.
- `/inventario [jogador]` — lista só os nomes dos jogadores que você possui, agrupados por posição, com o espaço usado no rodapé (ex: "5/8").

#### Limite de inventário
Cada jogador só cabe **8 cartas distintas** por padrão. Se uma carta nova (não duplicada) chegar com o inventário cheio, ela também vira Robux automaticamente — nada se perde, só não duplica o espaço. Pra aumentar o limite, use o botão **📦 Expandir Inventário** no `/loja`: cada compra custa **150 Robux** e adiciona **+4 espaços**, sem limite de quantas vezes você pode comprar.

#### Pacotes disponíveis na loja
| Pacote | Preço | Chances |
|---|---|---|
| **Básico 60+** | 60 Robux | Ouro 50% · Elite 28% · Dominante 15% · Immortal 5% · Lendário 1,8% · Mítico 0,2% |
| **Premium** | 100 Robux | Ouro 40% · Elite 30% · Dominante 18% · Immortal 8% · Lendário 3,5% · Mítico 0,5% |

#### Claim (grátis, cooldown de 20 min)
Sorteia entre **todas as 27 cartas** do catálogo, com chances: Ouro 65% · Elite 23% · Dominante 9% · Immortal 2,3% · Lendário 0,6% · Mítico 0,1%.

#### Weekly (grátis, cooldown de 7 dias)
Entrega **3 cartas**: a primeira é sempre overall 70+ (garantido), as outras duas são 100% aleatórias entre as 27. As 3 são reveladas uma de cada vez com uma pausa de suspense entre elas, sempre começando pela de **maior overall**.

### Duplicatas, inventário cheio, venda e troca
- **Autovenda automática**: se você já tem uma carta e ela sai de novo (pacote, claim, weekly ou trade), OU se seu inventário está cheio quando uma carta nova chegaria, ela **não duplica nem se perde** — em vez disso você recebe automaticamente o valor dela em Robux (o mesmo preço que aparece no `/info`).
  - Isso também foi aplicado **retroativamente**: na primeira vez que o bot rodar com essa atualização, qualquer duplicata que já existia antes é convertida em Robux automaticamente (mantendo 1 cópia de cada, o resto vira dinheiro). Rodar de novo depois não faz nada (é seguro, não duplica a conversão).
- `/vender nome` — vende manualmente uma carta do seu elenco pelo preço dela.
- `/trade oponente minha_carta carta_dele` — propõe trocar 1 carta sua por 1 carta de outra pessoa. O outro jogador recebe um pedido com botões **Aceitar/Recusar** (60s pra responder) — a troca só acontece se ele aceitar. Pra saber o que a outra pessoa tem, use `/inventario jogador:<ele>`.

### Escalação
- `/time_montar modo posicao slot jogador` — escala um jogador do seu elenco (pelo **nome**, com autocomplete das suas próprias cartas)
- `/time_ver modo [jogador]` — mostra sua escalação e o overall total
- `/time_remover modo posicao slot` — remove um jogador de um slot

Formações:
| Modo | GK | MC | ST |
|------|----|----|----|
| 4v4  | 1  | 1  | 2  |
| 7v7  | 1  | 3  | 3  |

### Como as partidas funcionam
Toda partida do bot (`/batalha`, `/amistoso`, `/campeonato`) roda numa **simulação de verdade**, não num sorteio de placar. Cada time tem sua força calculada a partir do overall dos jogadores em campo, e a partida evolui em sequências de ataque, chance, finalização e defesa — o placar é uma **consequência** do que acontece durante o jogo, nunca decidido de antemão. Isso permite jogos equilibrados (0-0, 1-0, 2-1...) e também goleadas de verdade (7-0, 9-1, 11-0...) quando um time realmente domina a partida.

### Batalha
- `/batalha oponente modo [aposta]` — desafia outro jogador. Se aceitar, a partida é **narrada ao vivo**: cruzamentos, chutes, cabeceios, defesas e gols envolvendo os jogadores reais das duas escalações, minuto a minuto, com intervalo no meio. No final aparece o placar, os **artilheiros de cada time** (com o nome do time em destaque acima da lista) e o **MVP da partida** (quem mais fez gol; sem gols, o de maior overall em campo). O placar decide quem leva a aposta.

### Amistoso (contra a máquina, partida única)
- `/amistoso modo` — enfrenta um time gerado pela máquina, com overall médio em torno de **83**, narrado ao vivo com o mesmo desfecho de artilheiros + MVP. Cooldown de 10 minutos. *(era `/campeonato` antes do torneio existir)*
  - Se você vencer, ganha **50 Robux**.
  - Times com overall médio **abaixo de 83 têm muito mais dificuldade** — não porque o placar é manipulado, mas porque o time fica com menos qualidade de jogo em campo (cria menos chances, defende pior). A partir de 83 de média o confronto fica justo, e acima disso as chances sobem bastante.

### Campeonato (torneio de mata-mata contra a máquina)
- `/campeonato modo` — torneio de 3 fases, cada uma contra um time da máquina mais forte que o anterior:

| Fase | Overall da máquina |
|---|---|
| Quartas de Final | 70+ |
| Semifinal | 75+ |
| Final | 80+ |

  - Ao usar o comando, aparece um botão **▶️ Iniciar Quartas de Final** — a partida só começa quando você clica.
  - Cada partida usa a mesma simulação ao vivo (eventos, placar, artilheiros, MVP) do resto do bot, só que o overall alvo da máquina muda por fase.
  - **Vencer** avança pra próxima fase com um novo botão **▶️ Continuar para a [fase]**. **Empate ou derrota elimina** você do torneio (mata-mata de verdade, sem pênaltis).
  - Vencer a **Final** (ser campeão) paga **100 Robux**. As fases anteriores não dão Robux, só a classificação.
  - Cooldown de **1 hora** pra iniciar um campeonato novo (não afeta trocar de fase dentro do mesmo torneio).

## ⚠️ Observações importantes

- O banco de dados é um arquivo local `dreamteam.db` (SQLite), criado automaticamente na primeira execução. Faça backup dele se for importante não perder o progresso dos jogadores.
- Se você mudar o código dos cogs, basta reiniciar o bot (`Ctrl+C` e rodar `python main.py` de novo).
- Todos os nomes de jogadores no catálogo são fictícios.

### Abertura de pacotes

Pacotes são abertos pelo `/inventario`. Na aba **Ver pacotes**, selecione um pacote, veja a imagem e clique em **Abrir pacotes**. Membros comuns podem abrir até **10** por vez; Server Boosters, até **20**.

As imagens opcionais dos pacotes ficam em `assets/pacotes/<chave_do_pacote>.png`.

Para dar um benefício de chance a Boosters, adicione `pesos_booster` dentro do pacote em `config.py`. Esse campo substitui `pesos` apenas quando um Booster abrir o pacote; se não existir, usa `pesos` normal.
