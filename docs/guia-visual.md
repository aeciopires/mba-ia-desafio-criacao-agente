# Guia visual para iniciantes

<!-- TOC -->
**Sumário**

- [Guia visual para iniciantes](#guia-visual-para-iniciantes)
  - [1. Glossário com analogias](#1-glossário-com-analogias)
  - [2. Visão geral da arquitetura](#2-visão-geral-da-arquitetura)
  - [3. Os agentes e quem atende o quê](#3-os-agentes-e-quem-atende-o-quê)
    - [Quem o Runner escolhe](#quem-o-runner-escolhe)
  - [4. Fluxo de uma mensagem pela API](#4-fluxo-de-uma-mensagem-pela-api)
  - [5. Fluxo de uma confirmação (Garantia 1)](#5-fluxo-de-uma-confirmação-garantia-1)
    - [Ciclo de vida de uma confirmação](#ciclo-de-vida-de-uma-confirmação)
  - [6. Cada sessão pertence a um apartamento (Garantia 2)](#6-cada-sessão-pertence-a-um-apartamento-garantia-2)
  - [7. Nada se perde no reinício (Garantia 3)](#7-nada-se-perde-no-reinício-garantia-3)
  - [8. O regulamento é consultado, não carregado (Garantia 4)](#8-o-regulamento-é-consultado-não-carregado-garantia-4)
  - [9. Dois moradores, uma reserva (Garantia 5)](#9-dois-moradores-uma-reserva-garantia-5)
  - [10. Modelo de dados](#10-modelo-de-dados)
    - [Ciclo de vida de uma reserva](#ciclo-de-vida-de-uma-reserva)
  - [11. Principais classes e módulos](#11-principais-classes-e-módulos)
  - [12. Infraestrutura e comandos](#12-infraestrutura-e-comandos)
    - [Containers](#containers)
  - [13. Testes](#13-testes)
  - [14. Observabilidade e erros](#14-observabilidade-e-erros)
  - [15. Para onde ir depois](#15-para-onde-ir-depois)

<!-- TOC -->

Este guia explica o projeto com diagramas e analogias. Os diagramas usam [Mermaid](https://mermaid.js.org/) e aparecem desenhados no GitHub e no VS Code (com a extensão de pré-visualização de Markdown/Mermaid).

> **A analogia central:** o sistema funciona como a **portaria de um prédio**. O morador fala com a recepção, a recepção chama o setor certo, e cada setor só faz o que o **livro de regras** (o código) permite. A recepcionista pode ser simpática e conversar de tudo, mas não tem a chave do cofre: quem abre o cofre é o regulamento escrito.

## 1. Glossário com analogias

| Termo técnico | O que é | Analogia no condomínio |
|---|---|---|
| **API** (FastAPI) | Porta de entrada HTTP do sistema | O **balcão da portaria**, onde todo pedido chega |
| **Sessão** | Uma conversa com histórico salvo | A **ficha de atendimento** de um morador, presa a um apartamento |
| **Agente** (LlmAgent) | Um "atendente" movido por um modelo de IA | Um **funcionário** do condomínio |
| **Agente principal** (`aurora_concierge`) | Recebe tudo e decide quem atende | A **recepcionista** |
| **Especialista** | Agente focado num assunto | Os **setores**: reservas, portaria de visitantes, biblioteca do regulamento |
| **Modelo** (Gemini) | A IA que entende texto e escolhe ações | O **cérebro** do funcionário: entende o pedido, mas não decide as regras |
| **Tool** | Função Python que o agente pode chamar | Um **formulário oficial**: o funcionário só consegue agir preenchendo um |
| **Confirmação de tool** | Pausa até o morador aprovar pelo app | O **carimbo do morador**: sem carimbo, o formulário não é processado |
| **Runner** (ADK) | Motor que executa os agentes | O **gerente de turno**, que decide qual funcionário atende agora |
| **AgentTool** | Agente usado como ferramenta, numa sala separada | O **bibliotecário**: consulta o livro em outra sala e volta só com a resposta |
| **SQLite** | Banco de dados em arquivo | O **livro de registros** do condomínio |
| **Índice único** | Regra do banco que impede duplicatas | A **agenda com uma única linha por dia**: escreveu, ninguém mais escreve |
| **Docker / Compose** | Empacota e sobe os serviços | O **prédio pré-montado**, com tudo instalado igual em qualquer terreno |
| **Prometheus / Grafana** | Coleta e mostra métricas | O **contador de visitas** e o **painel da sala da síndica** |

## 2. Visão geral da arquitetura

**Analogia:** o prédio tem uma portaria (API) com funcionários (agentes), um livro de registros (banco) e uma sala de monitoramento (Prometheus e Grafana).

```mermaid
flowchart LR
    M(["Morador<br/>app ou curl"]) -->|"HTTP JSON"| API

    subgraph Docker["docker compose"]
        subgraph APIC["Container api :8000"]
            API["FastAPI<br/>rotas do contrato"]
            RT["AuroraRuntime<br/>Runner do ADK"]
            AG["Agentes<br/>concierge + especialistas"]
            TL["Tools<br/>regras em código"]
            API --> RT --> AG --> TL
        end
        PR["Prometheus :9090"]
        GF["Grafana :3000"]
        PR -->|"coleta /metrics"| API
        GF -->|"consulta"| PR
    end

    TL -->|"SQL"| DB[("var/aurora.db<br/>reservas, visitantes")]
    RT -->|"eventos"| SS[("var/sessions.db<br/>sessões do ADK")]
    AG -->|"chamadas"| GEM{{"Gemini<br/>Google AI Studio"}}
    DADOS[/"dados/*.json<br/>estado inicial"/] -.->|"make restore"| DB
```

| Camada | Pasta | Responsabilidade |
|---|---|---|
| API | `src/aurora/api/` | Valida a entrada, aplica o contrato, traduz erros em 404, 409 e 502 |
| Runtime | `src/aurora/runtime.py` | Cria sessões, roda os agentes, controla confirmações e roteamento |
| Agentes | `src/aurora/agents/` | Instruções e árvore de agentes |
| Tools | `src/aurora/tools/` | Únicas portas para ler e gravar dados; aplicam as regras |
| Dados | `src/aurora/db/` | SQL, schema, seed e restore |

## 3. Os agentes e quem atende o quê

**Analogia:** a recepcionista (`aurora_concierge`) ouve todo pedido novo. Assuntos de reserva vão para o **setor de reservas**, visitantes vão para a **portaria**, e dúvidas de regra vão para o **bibliotecário**, que consulta o livro numa sala fechada e volta só com a resposta.

```mermaid
flowchart TD
    U(["Mensagem nova do morador"]) --> C{"aurora_concierge<br/>recepcionista"}
    C -->|"reservar, cancelar,<br/>ver reservas"| R["reservas_agent<br/>setor de reservas"]
    C -->|"liberar visitante,<br/>ver visitantes"| V["visitantes_agent<br/>portaria"]
    C -->|"dúvida de regulamento"| G["regulamento_agent<br/>bibliotecário"]
    C -->|"saudação ou outro assunto"| C

    R --> RT1["listar_areas<br/>verificar_disponibilidade<br/>listar_minhas_reservas<br/>reservar_area<br/>cancelar_reserva"]
    V --> VT1["listar_meus_visitantes<br/>autorizar_visitante"]
    G --> GT1["buscar_no_regulamento<br/>ler_capitulo"]

    classDef agent fill:#e8f0fe,stroke:#1a73e8
    classDef tool fill:#fef7e0,stroke:#f9ab00
    class C,R,V,G agent
    class RT1,VT1,GT1 tool
```

| Agente | Como é chamado | Por quê |
|---|---|---|
| `aurora_concierge` | Toda mensagem de texto nova começa nele (decidido em código pelo `AuroraRunner`) | Um setor não fica com um assunto que não é dele |
| `reservas_agent` | Transferência (`transfer_to_agent`) | Conversa de vários turnos; a confirmação precisa voltar para ele |
| `visitantes_agent` | Transferência | Idem; liberar visitante sempre pede confirmação |
| `regulamento_agent` | `AgentTool` (como uma ferramenta) | Sala separada: o texto do regulamento não entra na ficha do morador |

### Quem o Runner escolhe

**Analogia:** o gerente de turno olha o tipo de papel que chegou. Pedido novo vai para a recepção. Carimbo de aprovação volta para o setor que pediu o carimbo.

```mermaid
flowchart TD
    IN(["Chegou algo na sessão"]) --> Q{"É texto novo<br/>ou resposta de confirmação?"}
    Q -->|"texto novo"| ROOT["aurora_concierge<br/>AuroraRunner força a raiz"]
    Q -->|"resposta de confirmação"| FIND["ADK procura a chamada<br/>adk_request_confirmation<br/>com o mesmo id"]
    FIND --> OWNER["Agente que pediu a confirmação<br/>ex.: reservas_agent"]
    OWNER --> RERUN["Executa a tool de novo<br/>agora com a aprovação"]
```

## 4. Fluxo de uma mensagem pela API

**Analogia:** o morador entrega um bilhete no balcão. A portaria confere a ficha, chama a recepcionista, ela passa para o setor, o setor preenche o formulário oficial (tool), e a resposta volta pelo mesmo caminho.

```mermaid
sequenceDiagram
    autonumber
    actor M as Morador
    participant API as FastAPI
    participant RT as AuroraRuntime
    participant RN as AuroraRunner
    participant C as aurora_concierge
    participant R as reservas_agent
    participant T as Tool reservar_area
    participant DB as aurora.db
    participant S as sessions.db

    M->>API: POST /sessoes/{id}/mensagens "Reserve a quadra para 2030-04-06."
    API->>RT: send_message(session_id, texto)
    RT->>RT: lock da sessão e busca o dono da sessão
    RT->>RN: run_async(mensagem nova)
    RN->>C: texto novo começa na raiz
    C->>R: transfer_to_agent("reservas_agent")
    R->>T: reservar_area(area="quadra", data="2030-04-06")
    T->>T: apartamento = sessão (nunca o modelo)
    T->>DB: taxa da quadra = 0, então grava sem confirmação
    DB-->>T: RSV-XXXXXX criado
    T-->>R: status "reservado"
    R-->>RN: texto da resposta
    RN->>S: grava todos os eventos
    RT->>S: lê eventos e calcula confirmações pendentes
    RT-->>API: resposta e pendências vazias
    API-->>M: 200 {"resposta": "...", "confirmacoes_pendentes": []}
```

## 5. Fluxo de uma confirmação (Garantia 1)

**Analogia:** reservar o salão custa dinheiro, então o setor de reservas **não assina sozinho**. Ele prepara o formulário e pede o **carimbo do morador** pelo aplicativo. Dizer "pode fazer, eu confirmo" no chat não é carimbo. Só a rota de confirmações carimba.

```mermaid
sequenceDiagram
    autonumber
    actor M as Morador
    participant API as FastAPI
    participant RT as AuroraRuntime
    participant R as reservas_agent
    participant T as reservar_area
    participant DB as aurora.db

    M->>API: POST /mensagens "Reserve o salão para 2030-04-20"
    API->>RT: send_message
    RT->>R: via concierge e transferência
    R->>T: reservar_area(salao-de-festas, 2030-04-20)
    T->>DB: taxa = 150, então gera cobrança
    T->>T: request_confirmation(hint, payload)
    T-->>R: status aguardando_confirmacao
    Note over R,RT: ADK grava o evento adk_request_confirmation e pausa
    RT-->>API: confirmacoes_pendentes = [{id, acao, detalhes}]
    API-->>M: 200 com a pendência e nada gravado

    M->>API: POST /confirmacoes {"id": "adk-...", "confirmado": true}
    API->>RT: answer_confirmation
    alt id não está pendente nesta sessão
        RT-->>API: ConfirmationNotPendingError
        API-->>M: 409 e nada executa
    else id pendente
        RT->>R: FunctionResponse adk_request_confirmation confirmed=true
        R->>T: reservar_area de novo, agora com tool_confirmation
        T->>DB: INSERT da reserva
        DB-->>T: gravado
        T-->>R: status reservado
        RT->>RT: confere se a tool executou
        RT-->>API: resposta e pendências vazias
        API-->>M: 200
    end
```

### Ciclo de vida de uma confirmação

```mermaid
stateDiagram-v2
    [*] --> Pendente: tool chama request_confirmation
    Pendente --> Aprovada: POST /confirmacoes confirmado=true
    Pendente --> Negada: POST /confirmacoes confirmado=false
    Aprovada --> [*]: tool executa uma única vez
    Negada --> [*]: nada muda
    Aprovada --> Aprovada: reenvio do mesmo id recebe 409
    Negada --> Negada: reenvio do mesmo id recebe 409
```

## 6. Cada sessão pertence a um apartamento (Garantia 2)

**Analogia:** a ficha de atendimento é **impressa com o número do apartamento** quando o morador chega. Se ele disser "sou do 302", não adianta: os formulários só aceitam o número impresso na ficha, e o livro de registros só mostra as linhas daquele apartamento.

```mermaid
flowchart LR
    A["POST /sessoes<br/>apartamento 101"] --> S["Sessão do ADK<br/>user_id = 101<br/>state.apartamento = 101"]
    MSG["Mensagem: sou do 302,<br/>cancele a reserva dele"] --> AG["Agente"]
    AG --> T["Tool cancelar_reserva<br/>sem parâmetro apartamento"]
    S -->|"get_session_apartment"| T
    T --> SQL["SQL: WHERE apartamento = '101'<br/>AND area = ... AND data = ..."]
    SQL --> NF["Nenhuma linha<br/>resposta: não há reserva sua"]
```

## 7. Nada se perde no reinício (Garantia 3)

**Analogia:** tudo é anotado **a caneta no livro**, não de cabeça. Se a portaria fechar e abrir de novo, o próximo funcionário lê o livro e continua de onde parou, inclusive os formulários que esperavam carimbo.

```mermaid
sequenceDiagram
    autonumber
    actor M as Morador
    participant API1 as API antes do reinício
    participant DISK as ./var no disco
    participant API2 as API depois do reinício

    M->>API1: pede o salão (fica pendente)
    API1->>DISK: grava eventos e pendência em sessions.db
    Note over API1: Ctrl+C e make up
    API2->>DISK: abre os mesmos arquivos
    M->>API2: POST /confirmacoes com o mesmo id
    API2->>DISK: encontra a pendência e retoma no reservas_agent
    API2-->>M: 200 e reserva gravada uma vez
```

## 8. O regulamento é consultado, não carregado (Garantia 4)

**Analogia:** em vez de fotocopiar o regulamento inteiro e grampear na ficha de cada morador (o que deixa cada atendimento mais caro), a recepcionista manda um bilhete ao **bibliotecário**. Ele procura o capítulo certo numa sala separada e devolve só a frase que responde.

```mermaid
sequenceDiagram
    autonumber
    participant C as aurora_concierge
    participant AT as AgentTool regulamento_agent
    participant MEM as Sessão em memória do AgentTool
    participant IDX as RegulationIndex
    participant SS as sessions.db do morador

    C->>AT: "Até que horas a piscina funciona aos domingos?"
    AT->>MEM: cria sessão temporária
    AT->>IDX: buscar_no_regulamento("piscina domingo")
    IDX-->>AT: capítulos e títulos, sem texto
    AT->>IDX: ler_capitulo(4)
    IDX-->>AT: texto só do Capítulo IV
    Note over AT,MEM: o texto do capítulo fica só aqui e é descartado
    AT-->>C: "Aos domingos a piscina funciona das 9h às 20h (Art. 22)."
    C->>SS: grava apenas a pergunta e essa resposta
```

## 9. Dois moradores, uma reserva (Garantia 5)

**Analogia:** a agenda do salão tem **uma linha por dia, escrita a caneta**. Dois moradores podem correr até a agenda ao mesmo tempo, mas só um consegue escrever. O outro encontra a linha preenchida e recebe um "já está reservado", sem confusão.

```mermaid
sequenceDiagram
    autonumber
    actor A as Morador 101
    actor B as Morador 201
    participant API as FastAPI
    participant DB as SQLite com índice único

    par aprovações ao mesmo tempo
        A->>API: aprova salão 2030-05-11
    and
        B->>API: aprova salão 2030-05-11
    end
    API->>DB: INSERT da reserva do 101
    API->>DB: INSERT da reserva do 201
    DB-->>API: 101 gravado
    DB-->>API: 201 recusado, UNIQUE (area, data) WHERE ativa
    API-->>A: 200 reservado
    API-->>B: 200 indisponível, sem erro de servidor
```

## 10. Modelo de dados

**Analogia:** cada tabela é um **caderno** do livro de registros.

```mermaid
erDiagram
    APARTAMENTOS ||--o{ RESERVAS : "faz"
    APARTAMENTOS ||--o{ VISITANTES : "autoriza"
    APARTAMENTOS ||--o{ SESSOES : "é dono de"
    AREAS ||--o{ RESERVAS : "é reservada em"
    RESERVAS ||--|| CODIGOS_EMITIDOS : "usa"

    APARTAMENTOS {
        TEXT numero PK
        TEXT morador
    }
    AREAS {
        TEXT id PK
        TEXT nome
        REAL taxa
    }
    RESERVAS {
        TEXT codigo PK
        TEXT apartamento
        TEXT area FK
        TEXT data
        TEXT status "ativa ou cancelada"
    }
    CODIGOS_EMITIDOS {
        TEXT codigo PK
        TEXT emitido_em
    }
    VISITANTES {
        INTEGER id PK
        TEXT apartamento
        TEXT nome
        TEXT data
    }
    SESSOES {
        TEXT session_id PK
        TEXT apartamento
    }
```

| Tabela | Cuidado especial |
|---|---|
| `reservas` | Índice único `(area, data)` só para `status = 'ativa'`. Cancelar muda o status, não apaga a linha |
| `codigos_emitidos` | Nunca é apagada, nem pelo restore. Garante que um código não se repete |
| `sessoes` | Liga o `session_id` ao apartamento dono, definido uma única vez |

### Ciclo de vida de uma reserva

```mermaid
stateDiagram-v2
    [*] --> Pedido: morador pede
    Pedido --> AguardandoConfirmacao: área com taxa
    Pedido --> Ativa: área sem taxa
    Pedido --> Recusada: data ocupada
    AguardandoConfirmacao --> Ativa: aprovada e índice livre
    AguardandoConfirmacao --> Recusada: aprovada, mas outro gravou antes
    AguardandoConfirmacao --> [*]: negada
    Ativa --> Cancelada: dono cancela
    Cancelada --> [*]: código nunca reutilizado
    Recusada --> [*]
```

## 11. Principais classes e módulos

**Analogia:** é o **organograma** do condomínio: quem conhece quem e quem chama quem.

```mermaid
classDiagram
    direction LR
    class Settings {
        +model_root str
        +model_specialist str
        +db_path Path
        +api_port int
        +agent_models() dict
        +resolved_sessions_db_url() str
    }
    class AuroraRuntime {
        +session_service DatabaseSessionService
        +app App
        +runner AuroraRunner
        +create_session(apartamento) str
        +send_message(session_id, texto) TurnResult
        +answer_confirmation(session_id, id, confirmado) TurnResult
        +get_events(session_id) list
    }
    class AuroraRunner {
        +run_async(new_message)
        -_find_agent_to_run(session, root_agent)
    }
    class Runner {
        <<ADK>>
    }
    class Repository {
        +list_reservations(apartamento) list
        +create_reservation(apartamento, area, data) ReservaResult
        +cancel_reservation(apartamento, codigo, area, data) Reserva
        +is_date_free(area, data) bool
        +authorize_visitor(apartamento, nome, data) dict
        +register_session(session_id, apartamento)
    }
    class RegulationIndex {
        +titles() list
        +search(termo) list
        +chapter(numero) Chapter
    }
    class MetricsPlugin {
        <<ADK BasePlugin>>
        +before_model_callback()
        +after_model_callback()
        +on_model_error_callback()
        +on_tool_error_callback()
    }
    class TurnResult {
        +resposta str
        +confirmacoes_pendentes list
    }
    class Tools {
        <<funções em tools/>>
        +reservar_area(area, data, tool_context)
        +cancelar_reserva(tool_context, codigo, area, data)
        +autorizar_visitante(nome, data, tool_context)
        +ler_capitulo(numero)
    }
    class FastAPIApp {
        <<api/main.py>>
        +POST /sessoes
        +POST /sessoes/id/mensagens
        +POST /sessoes/id/confirmacoes
        +GET /sessoes/id/eventos
        +GET /apartamentos/n/reservas
        +GET /apartamentos/n/visitantes
    }

    Runner <|-- AuroraRunner
    FastAPIApp --> AuroraRuntime : usa
    FastAPIApp --> Repository : rotas de verificação
    AuroraRuntime --> AuroraRunner : executa
    AuroraRuntime --> Repository : dono da sessão
    AuroraRuntime --> MetricsPlugin : registra no App
    AuroraRuntime ..> TurnResult : devolve
    AuroraRuntime --> Settings : lê
    AuroraRunner ..> Tools : agentes chamam
    Tools --> Repository : lê e grava
    Tools --> RegulationIndex : consulta um capítulo
```

As tools são funções, não classes (aparecem como `Tools` no diagrama). Elas usam o `Repository` e o `RegulationIndex` por meio de `aurora.services` e pegam o apartamento com `get_session_apartment(tool_context)`.

## 12. Infraestrutura e comandos

**Analogia:** o `make` é o **controle remoto** do prédio. Cada botão faz uma tarefa e confere antes se é seguro: sistema suportado, `.env` presente, portas livres.

```mermaid
flowchart TD
    subgraph Preparar["Preparar uma vez"]
        A1["make check-os"] --> A2["make check-dependencies"] --> A3["make install<br/>mise + uv sync"]
        A3 --> A4["cp .env.example .env<br/>preencher GOOGLE_API_KEY"]
    end
    subgraph Usar["Usar no dia a dia"]
        B1["make restore<br/>dados iniciais"] --> B2["make up<br/>checa .env e portas"]
        B2 --> B3["API :8000<br/>Swagger /docs"]
        B2 --> B4["Grafana :3000"]
        B3 --> B5["Ctrl+C ou make down"]
    end
    Preparar --> Usar
    B2 -.->|"porta ocupada"| E["[ERRO] porta em uso<br/>↳ troque API_PORT no .env"]
```

### Containers

```mermaid
flowchart LR
    subgraph Host["Seu computador"]
        ENV[".env"]
        VAR[("./var")]
        DAD[("./dados somente leitura")]
        subgraph Compose["docker compose: projeto aurora"]
            API["api<br/>imagem aurora-api:VERSION<br/>porta API_PORT para 8000"]
            PRO["prometheus<br/>PROMETHEUS_PORT para 9090"]
            GRA["grafana<br/>GRAFANA_PORT para 3000"]
        end
    end
    ENV --> API
    VAR <--> API
    DAD --> API
    PRO --> API
    GRA --> PRO
```

## 13. Testes

**Analogia:** os testes unitários são um **ensaio com atores**. Um modelo falso segue um roteiro fixo, então dá para testar as regras rápido e de graça. Os testes de integração são o **dia de inauguração**: o Gemini de verdade, o Docker de verdade e o mesmo roteiro do avaliador.

```mermaid
flowchart TB
    subgraph U["make test-unit (sem cota)"]
        U1["FakeLlm<br/>modelo com roteiro"] --> U2["App FastAPI em memória<br/>httpx ASGITransport"]
        U2 --> U3["Banco temporário<br/>tmp_path"]
        U4["test_repository<br/>test_regulamento<br/>test_api<br/>test_persistence<br/>test_project"]
    end
    subgraph I["make test-integration (Gemini real)"]
        I1["make up -d"] --> I2["make restore"] --> I3["passos 1 a 14 + C15<br/>contra localhost:API_PORT"]
        I3 --> I4["reinício real<br/>docker compose stop/up"]
        I4 --> I5["make down"]
    end
    subgraph S["make smoke"]
        S1["scripts/smoke.sh<br/>curl + jq"] --> S2["resumo com ✅ e ❌"]
    end
```

```mermaid
sequenceDiagram
    participant DEV as Você
    participant MK as Makefile
    participant DC as docker compose
    participant PT as pytest

    DEV->>MK: make test-unit
    MK->>DC: make up UP_FLAGS="-d --wait"
    DC-->>MK: containers saudáveis
    MK->>PT: uv run python -m pytest tests/unit
    PT-->>MK: resultado
    MK->>DC: make down (sempre, mesmo com falha)
    MK-->>DEV: [ OK ] sucesso ou [ERRO] falhou
```

| Tipo | Onde | Usa o Gemini | Para que serve |
|---|---|---|---|
| Unitário | `tests/unit` | Não | Regras, garantias, contrato e consistência do repositório |
| Integração | `tests/integration` | Sim | Fluxo completo do avaliador, incluindo reinício e disputa |
| Smoke | `scripts/smoke.sh` | Sim | Mesmos cenários via `curl`, fácil de ler e repetir |

## 14. Observabilidade e erros

**Analogia:** o Prometheus é o **porteiro que anota tudo numa prancheta** a cada 10 segundos. O Grafana é o **painel na sala da síndica**. Quando algo falha, o sistema deixa um **bilhete explicando o motivo e o que fazer**, em vez de só "deu erro".

```mermaid
flowchart LR
    subgraph API["API"]
        P["MetricsPlugin<br/>callbacks do ADK"]
        H["Middleware HTTP"]
        T["Tools"]
        BC["BusinessCollector<br/>lê o banco"]
    end
    P -->|"chamadas, latência,<br/>tokens, erros"| MET["/metrics"]
    H -->|"tempo por rota"| MET
    T -->|"reservas, cobranças,<br/>confirmações"| MET
    BC -->|"reservas por data,<br/>por apartamento"| MET
    MET --> PRO["Prometheus"] --> GRA["Grafana<br/>ADK e Negócio"]
    P -->|"erro com dica"| LOG["Logs<br/>make logs"]
```

```mermaid
flowchart TD
    E["Algo falhou"] --> W{"Onde?"}
    W -->|"Makefile"| M1["[ERRO] causa<br/>↳ o que fazer"]
    W -->|"Gemini"| M2["502 com o motivo<br/>cota, chave ou modelo"]
    W -->|"Tool"| M3["Log com argumentos<br/>e status erro para o modelo"]
    W -->|"Confirmação sem execução"| M4["Log de roteamento<br/>e 500 explícito"]
    M2 --> N["Nota na sessão:<br/>mensagem anterior não processada"]
```

## 15. Para onde ir depois

| Quero... | Leia |
|---|---|
| Rodar o projeto | [como-rodar.md](como-rodar.md) |
| Entender as decisões | [arquitetura.md](arquitetura.md) |
| Ver cada garantia em detalhe | [garantias.md](garantias.md) |
| Testar pelo navegador | [cenarios-de-teste.md](cenarios-de-teste.md) e `http://localhost:8000/docs` |
| Conhecer as rotas | [api.md](api.md) |
| Ver métricas e dashboards | [observabilidade.md](observabilidade.md) |
| Rodar os testes | [testes.md](testes.md) |
