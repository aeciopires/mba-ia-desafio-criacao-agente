# CLAUDE.md — instruções e guardrails do repositório

<!-- TOC -->
**Sumário**

- [1. Fonte da verdade e precedência](#1-fonte-da-verdade-e-precedência)
- [2. Guardrails invioláveis (nunca fazer)](#2-guardrails-invioláveis-nunca-fazer)
- [3. Convenções](#3-convenções)
- [4. Regras de sincronização (manter tudo consistente)](#4-regras-de-sincronização-manter-tudo-consistente)
- [5. Definição de pronto para qualquer mudança](#5-definição-de-pronto-para-qualquer-mudança)
- [6. Comandos úteis](#6-comandos-úteis)
- [7. Armadilhas conhecidas](#7-armadilhas-conhecidas)
- [8. Atualização de dependências (somente quando explicitamente solicitada)](#8-atualização-de-dependências-somente-quando-explicitamente-solicitada)
<!-- /TOC -->

Contrato de trabalho para agentes de código (e pessoas) que alteram este repositório. A versão para pessoas é o [CONTRIBUTING.md](CONTRIBUTING.md); os dois não podem se contradizer.

## 1. Fonte da verdade e precedência

1. [TASK.md](TASK.md) define o escopo e o contrato da API. Em conflito, vale o `TASK.md`.
2. Depois vem o [PLAN.md](PLAN.md), e por último o código existente.
3. Toda decisão que o `TASK.md` deixa livre (topologia de agentes, modelos, armazenamento, comportamento do restore) é registrada no README ou em `docs/`, com o motivo.

## 2. Guardrails invioláveis (nunca fazer)

- Alterar qualquer arquivo em `dados/` (conferir com `git diff --exit-code -- dados/`).
- Versionar chaves ou credenciais. `.env` e `gemini.yaml` ficam fora do Git, e o `.env.example` só tem nomes de variáveis, sem valores.
- Criar tool com parâmetro `apartamento`, ou qualquer caminho em que o apartamento venha do modelo e não da sessão (`aurora.tools.context.get_session_apartment`).
- Colocar regra crítica só no prompt. Confirmação, posse do apartamento e exclusividade da reserva ficam em código.
- Colocar o regulamento nas instruções do agente principal, ou fazer uma tool devolver mais de um capítulo.
- Fazer uma tool ou resposta expor código de reserva, nome de visitante ou número de apartamento de outro morador.
- Apagar reservas fisicamente, limpar `codigos_emitidos` ou reutilizar códigos (inclusive de reservas canceladas).
- Remover o índice único parcial `ux_reserva_ativa`, ou trocá-lo por uma checagem só antes de gravar.
- Definir `disallow_transfer_to_parent=True` nos especialistas ou desligar a `resumability` sem refazer o spike de confirmação (ver `docs/arquitetura.md`). Isso faz a aprovação ser aceita sem executar nada.
- Mudar caminhos, campos ou códigos de status do contrato da API.
- Trocar a versão exata do ADK sem atualizar `uv.lock`, README e testes, ou sair da série 2 / ficar abaixo da 2.2.0.
- Escrever o número da versão do projeto em qualquer lugar além do arquivo `VERSION`.
- Atualizar dependências por iniciativa própria (ver seção 8).

## 3. Convenções

- Código, comentários, nomes e mensagens de commit em **en-US**. Documentação (README, `docs/`, `CHANGELOG.md`, `CONTRIBUTING.md`, `REQUIREMENTS*.md`) em **pt-BR**.
- Python ≥ 3.12 gerenciado por uv (`pyproject.toml` + `uv.lock`). Ferramentas via `mise.toml`. Docker, Docker Compose e Colima vêm do sistema operacional.
- Estrutura:
  - `src/aurora/{api,agents,tools,db,regulamento}`
  - `tests/{unit,integration}`
  - `scripts/`, `observability/`, `docs/`
- Mensagens de erro (Makefile, scripts e API) dizem a causa e o que fazer (`[ERRO] ...` + `↳ dica`).
- **Sumário (TOC) em todo arquivo `.md`:**
  - fica logo após o título `#`, entre `<!-- TOC -->` e `<!-- /TOC -->`, e lista os títulos `##` e `###`;
  - é gerado por `make toc` (`scripts/gen_toc.py`); não edite o bloco à mão;
  - todo `.md` novo ganha o sumário ao rodar `make toc`;
  - exceção: `dados/` (não pode ser alterado).
- **Diagramas Mermaid e analogias na documentação** (público: iniciantes):
  - o [docs/guia-visual.md](docs/guia-visual.md) é o guia ilustrado do projeto: glossário com analogias, arquitetura, agentes e roteamento, fluxos da API (mensagem, confirmação, reinício, regulamento, disputa), estados, modelo de dados, classes, infraestrutura, testes e observabilidade;
  - todo diagrama novo ou alterado vem com uma frase de **analogia** antes dele, usando a metáfora do condomínio: portaria = API, recepcionista = agente principal, setores = especialistas, formulário oficial = tool, carimbo do morador = confirmação, livro de registros = banco, bibliotecário = `AgentTool`;
  - diagramas ficam em blocos ` ```mermaid `, com rótulos entre aspas quando tiverem símbolos, e precisam passar em `make check-diagrams`;
  - README e `docs/arquitetura.md` mantêm uma versão resumida da arquitetura em Mermaid; o detalhe fica no guia visual;
  - não use imagens geradas (PNG/SVG) no lugar do Mermaid: o diagrama precisa ser editável em texto.

## 4. Regras de sincronização (manter tudo consistente)

| Se você mudou... | Atualize também |
|---|---|
| Uma garantia (arquivo, função ou linha) | Tabela **Garantias** do README e `docs/garantias.md`. Os links `arquivo#Lnn` precisam existir (há teste). |
| A topologia de agentes | **Arquitetura** no README e `docs/arquitetura.md`, com o motivo |
| Uma variável de ambiente | `.env.example`, tabela do README e `docs/como-rodar.md` |
| Um alvo do Makefile | Comentário `##` (aparece em `make help`) e `docs/como-rodar.md` |
| Uma rota ou schema | Exemplos e respostas OpenAPI, `make openapi`, `docs/api.md`, `docs/cenarios-de-teste.md`, `scripts/api.sh`, `scripts/smoke.sh` e testes de integração |
| Uma métrica | `scripts/gen_dashboards.py` + `make dashboards` e `docs/observabilidade.md` |
| Uma fase ou decisão do plano | `PLAN.md` |
| Componentes, agentes, roteamento, rotas, fluxo de confirmação, tabelas do banco, classes ou módulos principais, alvos de teste, serviços do compose ou métricas | Os diagramas e analogias correspondentes em `docs/guia-visual.md`, e o diagrama resumido do README e de `docs/arquitetura.md` se a arquitetura mudou. Depois rode `make check-diagrams`. |
| Qualquer título (`##`/`###`) ou arquivo `.md` novo | `make toc` (o teste `test_markdown_tocs_are_current` e o `make lint` falham se o sumário estiver desatualizado) |
| Qualquer coisa visível (funcionalidade, correção, rota, variável, alvo, decisão) | Entrada em `## [Unreleased]` no `CHANGELOG.md` |
| A versão do projeto | Só o `VERSION`; transforme `[Unreleased]` na seção da versão no `CHANGELOG.md` |
| A lista de sistemas suportados | `SUPPORTED_UBUNTU` no Makefile e em `scripts/lib.sh`, `scripts/check-os.sh`, README, `docs/como-rodar.md`, o `docs/requirements/REQUIREMENTS-<so>.md` correspondente e a tabela do `REQUIREMENTS.md` |
| Uma dependência de sistema ou ferramenta | `scripts/check-deps.sh`, `REQUIREMENTS.md` e **todos** os `docs/requirements/REQUIREMENTS-<so>.md`, com o link oficial |
| Portas ou serviços do compose | `scripts/check-ports.sh`, `.env.example`, README e `docs/como-rodar.md` |
| O fluxo de contribuição, testes obrigatórios ou guardrails | `CONTRIBUTING.md` junto com este arquivo |

## 5. Definição de pronto para qualquer mudança

- `make lint` (inclui a checagem dos sumários) e `make test-unit` verdes.
- Se a mudança afetou algo desenhado no guia visual: diagramas e analogias atualizados e `make check-diagrams` verde. Se a mudança tocar agentes, tools ou API, também `make test-integration`.
- `git diff --exit-code -- dados/` limpo e nenhum segredo no diff.
- Entrada correspondente no `CHANGELOG.md`.
- Checklist da seção 15 do `PLAN.md` revisado para os itens afetados.

## 6. Comandos úteis

`make help` · `make check-os` · `make check-dependencies` · `make requirements` · `make version` · `make install` · `make build` · `make build-multiarch` · `make up` · `make down` · `make restore` · `make reset` · `make logs` · `make swagger` · `make openapi` · `make test-unit` · `make test-integration` · `make smoke` · `make lint` · `make fmt` · `make toc` · `make check-diagrams` · `make dashboards`

## 7. Armadilhas conhecidas

- **Confirmação aceita sem executar:** acontece quando o Runner entrega a resposta ao agente errado. Hoje a resposta chega ao agente certo por causa do `App` resumível com especialistas transferíveis. A rota confere se a tool executou e loga `Confirmation ... was stored but the tool did not run`. Teste sempre com sessão persistida e após reinício (cenário C15).
- **Roteamento de mensagens novas:** o `AuroraRunner` força o agente principal em toda mensagem de texto nova. Não remova isso sem medir com os testes de integração.
- **Cotas do Gemini:** chaves gratuitas têm limites baixos por modelo, por minuto e por dia. Use `AURORA_MODEL_*` por agente para dividir a carga.
- **Ambiente em `.env`:** variáveis vazias usam o padrão (`env_ignore_empty`). Dentro do container a API escuta sempre na 8000.

## 8. Atualização de dependências (somente quando explicitamente solicitada)

- Só atualize quando a pessoa pedir de forma explícita (ex.: "atualize as dependências"). Nunca como efeito colateral de outra tarefa.
- **Escopo:**
  - pacotes Python em `pyproject.toml` e `uv.lock` (`uv lock --upgrade` e depois fixar versões exatas no `pyproject.toml`);
  - ferramentas no `mise.toml` (Python, uv, jq);
  - imagens base do `Dockerfile` (`ghcr.io/astral-sh/uv`, `python:3.12.x-slim-*`);
  - imagens do Prometheus e do Grafana no `docker-compose.yml`;
  - versões de referência do Colima, Docker CLI, Compose e Buildx no macOS (Homebrew, fora do mise) e flags recomendadas do `colima start`;
  - modelos Gemini padrão em `src/aurora/config.py`, se a pessoa pedir;
  - arquivos de requisitos: `REQUIREMENTS.md` e todos os `docs/requirements/REQUIREMENTS-<so>.md`.
- **Manutenção dos arquivos de requisitos** (obrigatória em toda atualização):
  - atualizar a tabela "Versões de referência" de cada arquivo e a data da revisão;
  - reabrir as páginas oficiais de instalação e ajustar comandos, pacotes, repositórios e codinomes que mudaram:
    - Docker Engine para Ubuntu: <https://docs.docker.com/engine/install/ubuntu/>
    - pós-instalação no Linux: <https://docs.docker.com/engine/install/linux-postinstall/>
    - build multi-plataforma: <https://docs.docker.com/build/building/multi-platform/>
    - Colima: <https://github.com/abiosoft/colima>
    - mise: <https://mise.jdx.dev/installing-mise.html>
    - uv: <https://docs.astral.sh/uv/>
  - conferir se cada link oficial ainda responde e aponta para a página certa;
  - quando um sistema ganhar ou perder suporte de alguma dependência, refletir isso no arquivo do sistema, no `REQUIREMENTS.md`, no `check-os` e no `CHANGELOG.md`;
  - garantir que os passos manuais e o `make check-dependencies`/`make install` continuam equivalentes;
  - revisar o `CONTRIBUTING.md` se a preparação do ambiente mudar.
- **Fontes:** só oficiais (PyPI, releases do projeto, Docker Hub/GHCR oficial, documentação oficial). Leia as notas de versão e registre mudanças incompatíveis.
- **Restrições do `TASK.md` que continuam valendo:** Google ADK na série 2, ≥ 2.2.0, versão exata fixada; Python ≥ 3.12; Docker e Docker Compose fora do mise.
- **Sempre fixe versões exatas.** Nada de `latest`, `^` ou `~` em imagens e ferramentas.
- **Validação obrigatória:** `make check-dependencies`, `make build`, `make build-multiarch`, `make test-unit`, `make test-integration` (inclui reinício e disputa) e `make smoke`.
- **Registro:**
  - suba a versão em `VERSION`: *patch* para atualização compatível, *minor* se o comportamento mudar;
  - abra a seção no `CHANGELOG.md` com versão antiga → nova em `Alterado`/`Segurança`;
  - atualize README, `docs/` e arquivos de requisitos onde as versões aparecem.
