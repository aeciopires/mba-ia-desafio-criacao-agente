# Garantias

<!-- TOC -->
**Sumário**

- [1. Cobrança ou acesso só com confirmação](#1-cobrança-ou-acesso-só-com-confirmação)
- [2. Cada sessão pertence a um apartamento](#2-cada-sessão-pertence-a-um-apartamento)
- [3. Nada se perde no reinício](#3-nada-se-perde-no-reinício)
- [4. O regulamento é consultado, não carregado](#4-o-regulamento-é-consultado-não-carregado)
- [5. Dois moradores, uma reserva](#5-dois-moradores-uma-reserva)
<!-- /TOC -->

Cada garantia é implementada em código e coberta por testes unitários (modelo falso) e de integração (Gemini real). Ponteiros de arquivo e linha: tabela **Garantias** do [README](../README.md#garantias).

> Diagramas e analogias: [guia-visual.md](guia-visual.md).

## 1. Cobrança ou acesso só com confirmação

- **Quem decide:** a tool, não o prompt.
  - `reservar_area` consulta a taxa no banco e, se `taxa > 0`, chama `tool_context.request_confirmation(hint, payload)`.
  - `autorizar_visitante` sempre chama.
- **Quando grava:** só quando `tool_context.tool_confirmation.confirmed` é verdadeiro. Negar devolve "cancelado" e não muda nada.
- **Pendências:** são calculadas dos eventos persistidos (`adk_request_confirmation` sem resposta com o mesmo `id`). Por isso sobrevivem a reinícios e são isoladas por sessão.
- **Rota de confirmações:**
  - um lock por sessão serializa as respostas;
  - `id` que não está pendente na sessão (inexistente, de outra sessão ou já respondido) → **409**, sem executar nada;
  - depois de retomar, a rota confere se a tool realmente rodou.
- **Sem confirmação:** área com taxa 0 (quadra) e cancelamento da própria reserva.
- **Testes:** `test_charged_reservation_deny_approve_and_replay`, `test_confirmation_id_from_other_session_is_409`, `test_visitor_always_needs_system_confirmation`; integração: passos 6 a 9 e 11.

## 2. Cada sessão pertence a um apartamento

- **Criação:** `POST /sessoes` cria a sessão do ADK com `user_id = apartamento` e `state["apartamento"]`, e registra o dono na tabela `sessoes`.
- **Origem do apartamento:** `get_session_apartment(tool_context)` lê o `user_id` e confere com o `state`. Nenhuma tool aceita apartamento como parâmetro.
- **Filtros por dono no SQL:**
  - listar reservas e visitantes: `WHERE apartamento = ?`;
  - cancelar: o filtro de dono faz parte da consulta, então código, área e data de outro apartamento nunca casam;
  - resposta "não encontrada": a mesma, exista a reserva ou não.
- **Disponibilidade:** devolve só `disponivel: true/false`. Reservar uma data ocupada devolve "indisponível", sem código nem apartamento.
- **Testes:** `test_other_apartment_data_never_reaches_the_session`, `test_taken_date_is_refused_without_leaking`, `test_cancel_only_matches_own_apartment`; integração: passos 3, 4 e 10.

## 3. Nada se perde no reinício

- **Sessões:** `DatabaseSessionService` (SQLAlchemy + aiosqlite) em `./var/sessions.db`. Dados do condomínio em `./var/aurora.db`. Os dois ficam num bind mount, fora do container.
- **App resumível:** uma aprovação depois do reinício retoma a invocação pausada no agente certo.
- **Testes:** `test_session_and_pending_confirmation_survive_restart` recria todo o runtime sobre os mesmos arquivos. Integração: passo 13 (`docker compose stop/up` real) e cenário C15 (confirmação pedida antes e aprovada depois do reinício).

## 4. O regulamento é consultado, não carregado

- **Agente principal:** não tem o regulamento nas instruções. Um teste verifica que nenhuma linha do regulamento aparece em `ROOT_INSTRUCTION`.
- **`regulamento_agent`:** roda como `AgentTool`, numa sessão em memória própria. Para a sessão do morador volta só a resposta final.
- **Tools:**
  - `buscar_no_regulamento` devolve números e títulos de capítulos;
  - `ler_capitulo` devolve um único capítulo, recortado pelo cabeçalho `## Capítulo`.
- **Testes:** `test_regulation_answer_without_loading_other_chapters` verifica que os eventos têm chamadas de tool e não têm trechos de outros capítulos (nem do próprio capítulo da piscina). Integração: passo 12.

## 5. Dois moradores, uma reserva

- **Índice único parcial:** `CREATE UNIQUE INDEX ux_reserva_ativa ON reservas(area, data) WHERE status = 'ativa'`.
- **Gravação:** em `BEGIN IMMEDIATE`, inserindo o código em `codigos_emitidos` e a reserva na mesma transação. Se o índice recusar, a tool responde "indisponível" (HTTP 200).
- **Conferência antes de gravar:** existe só para responder rápido e não pedir confirmação de algo impossível. Ela não é a garantia.
- **Códigos:** `RSV-` + 6 caracteres aleatórios, únicos por chave primária em `codigos_emitidos`. Essa tabela nunca é apagada, nem pelo restore, então um código nunca se repete (regra de negócio 5).
- **Testes:** `test_concurrent_reservations_have_a_single_winner` (24 threads), `test_concurrent_approvals_single_reservation`; integração: passo 14.
