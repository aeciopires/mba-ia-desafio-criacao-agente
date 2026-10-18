# Como contribuir

<!-- TOC -->
**Sumário**

- [Como contribuir](#como-contribuir)
  - [1. Preparar o ambiente](#1-preparar-o-ambiente)
  - [2. Fluxo de trabalho](#2-fluxo-de-trabalho)
  - [Fluxo de commits e pull requests](#fluxo-de-commits-e-pull-requests)
  - [3. Convenções](#3-convenções)
  - [4. Regras que não podem ser quebradas](#4-regras-que-não-podem-ser-quebradas)
  - [5. Testes obrigatórios antes do PR](#5-testes-obrigatórios-antes-do-pr)
  - [6. Checklist do PR](#6-checklist-do-pr)
  - [7. Atualização de dependências](#7-atualização-de-dependências)

<!-- TOC -->

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

## Fluxo de commits e pull requests

Use um fork para propor alterações. Configure a autenticação SSH do GitHub
conforme a [documentação oficial](https://docs.github.com/authentication/connecting-to-github-with-ssh)
e siga estes passos:

1. Crie um fork de `aeciopires/mba-ia-desafio-criacao-agente` no GitHub e clone-o:

   ```bash
   git clone git@github.com:SEU_USUARIO/mba-ia-desafio-criacao-agente.git
   cd mba-ia-desafio-criacao-agente
   ```

2. Registre o repositório original como `upstream` e confira os remotos:

   ```bash
   git remote add upstream git@github.com:aeciopires/mba-ia-desafio-criacao-agente.git
   git remote -v
   ```

3. Atualize a branch principal local e crie uma branch para sua alteração:

   ```bash
   git switch main
   git pull upstream main
   git switch -c tipo/descricao-curta
   ```

   Use um nome simples e descritivo para a branch, por exemplo
   `docs/guia-de-instalacao` ou `fix/carregamento-agente`.

4. Faça e valide as alterações. Revise o diff e confirme que somente os arquivos
   pretendidos serão incluídos:

   ```bash
   git status --short
   git diff --check
   git diff
   ```

5. Adicione os arquivos pertinentes, crie commits focados com mensagens
   descritivas e envie a branch ao seu fork:

   ```bash
   git add caminho/do/arquivo
   git commit -m "docs: descreve a estrutura do projeto"
   git push --set-upstream origin tipo/descricao-curta
   ```

   Não inclua credenciais, arquivos `.env`, ambientes virtuais nem outros
   arquivos locais no commit. Se houver mais de uma alteração independente,
   prefira separá-las em commits claros.

6. No GitHub, abra um pull request do seu fork para a branch `main` do
   repositório original. Descreva o objetivo, resuma as mudanças e informe as
   validações executadas. Considere e responda às sugestões da revisão; envie
   novos commits à mesma branch quando fizer ajustes.

7. Após o merge, atualize sua branch principal e, se desejar, remova a branch de
   trabalho:

   ```bash
   git switch main
   git pull upstream main
   git push origin main
   git branch -d tipo/descricao-curta
   git push origin --delete tipo/descricao-curta
   ```

Para sincronizar o fork posteriormente, estando na branch `main`, execute:

```bash
git pull upstream main
git push origin main
```

Contribuições estão sujeitas aos termos da licença MIT deste repositório.

## 3. Convenções

- Código, comentários e nomes em en-US. Documentação em pt-BR.
- Estrutura: `src/aurora/{api,agents,tools,db,regulamento}`, `tests/{unit,integration}`, `scripts/`, `observability/` e `docs/`.
- Mensagens de erro dizem a causa e o que fazer.
- Todo arquivo `.md` tem um sumário (TOC) logo após o título, gerado por `make toc`, com os títulos `#`, `##` e `###` (igual aos plugins de TOC dos editores). O bloco fica entre duas marcas `<!-- TOC -->` (não use `<!-- /TOC -->`, que conflita com plugins de editor). Não edite o bloco à mão; o `make toc` é idempotente e remove sumários duplicados.
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
