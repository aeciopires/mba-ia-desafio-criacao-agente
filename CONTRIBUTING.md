# Como contribuir

<!-- TOC -->
**Sumário**

- [1. Preparar o ambiente](#1-preparar-o-ambiente)
- [2. Fluxo de trabalho](#2-fluxo-de-trabalho)
- [3. Convenções](#3-convenções)
- [4. Regras que não podem ser quebradas](#4-regras-que-não-podem-ser-quebradas)
- [5. Testes obrigatórios antes do PR](#5-testes-obrigatórios-antes-do-pr)
- [6. Checklist do PR](#6-checklist-do-pr)
- [7. Atualização de dependências](#7-atualização-de-dependências)
<!-- /TOC -->

Obrigado por contribuir com o assistente do Residencial Aurora! Este guia é para pessoas. Agentes de código seguem o [CLAUDE.md](CLAUDE.md), que tem as mesmas regras com mais detalhes.

## 1. Preparar o ambiente

1. Leia o [REQUIREMENTS.md](REQUIREMENTS.md). Ele indica o arquivo de requisitos do seu sistema.
2. Rode as checagens e a instalação:
   ```bash
   make check-os
   make check-dependencies
   make install
   ```
3. Configure o ambiente:
   ```bash
   cp .env.example .env    # preencha GOOGLE_API_KEY (Google AI Studio)
   ```
4. Suba e teste:
   ```bash
   make restore && make up
   ```

Se alguma porta estiver ocupada, troque `API_PORT`, `PROMETHEUS_PORT` ou `GRAFANA_PORT` no `.env`.

## 2. Fluxo de trabalho

1. Faça um fork e crie uma branch a partir da `main`: `feat/...`, `fix/...`, `docs/...` ou `chore/...`.
2. Escreva os commits no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/), em en-US. Exemplo: `fix: return 409 for answered confirmations`.
3. Abra o pull request para a `main` com o checklist da seção 6 preenchido.

## 3. Convenções

- Código, comentários e nomes em en-US. Documentação em pt-BR.
- Estrutura: `src/aurora/{api,agents,tools,db,regulamento}`, `tests/{unit,integration}`, `scripts/`, `observability/` e `docs/`.
- Mensagens de erro dizem a causa e o que fazer.
- Todo arquivo `.md` tem um sumário (TOC) logo após o título, gerado por `make toc`. Não edite o bloco `<!-- TOC -->` à mão.
- A documentação é escrita para iniciantes: diagramas em Mermaid, cada um com uma analogia do condomínio (veja o [guia visual](docs/guia-visual.md)). Se mudar algo que aparece num diagrama, atualize o diagrama e rode `make check-diagrams`.

## 4. Regras que não podem ser quebradas

Resumo dos guardrails (lista completa no [CLAUDE.md](CLAUDE.md#2-guardrails-invioláveis-nunca-fazer)):

- Não altere `dados/` e não versione segredos (`.env`, `gemini.yaml`).
- O apartamento vem sempre da sessão; nenhuma tool recebe apartamento.
- Confirmação, posse do apartamento e exclusividade da reserva ficam em código, nunca só no prompt.
- O regulamento nunca entra nas instruções do agente principal nem no histórico da sessão.
- O contrato da API (`TASK.md`) não muda.
- A versão do projeto só muda no arquivo `VERSION`.

## 5. Testes obrigatórios antes do PR

```bash
make lint
make test-unit
make test-integration      # se mexeu em agentes, tools ou API
make smoke && make openapi # se mexeu na API
```

## 6. Checklist do PR

- [ ] `make lint`, `make test-unit` (e `make test-integration` quando aplicável) verdes.
- [ ] Diagramas e analogias de `docs/guia-visual.md` atualizados, se a mudança afetou o que eles mostram (`make check-diagrams`).
- [ ] `make toc` rodado se você criou ou renomeou títulos ou arquivos `.md`.
- [ ] Entrada em `## [Unreleased]` no [CHANGELOG.md](CHANGELOG.md).
- [ ] README e `docs/` atualizados conforme as regras de sincronização do `CLAUDE.md`.
- [ ] `git diff --exit-code -- dados/` limpo e nenhum segredo no diff.
- [ ] `make check-os` ok no seu sistema.

## 7. Atualização de dependências

Só com pedido explícito, seguindo o procedimento do [CLAUDE.md](CLAUDE.md#8-atualização-de-dependências-somente-quando-explicitamente-solicitada). Inclui revisar o `REQUIREMENTS.md`, os arquivos em `docs/requirements/` e as versões de referência, e validar com todos os testes.
