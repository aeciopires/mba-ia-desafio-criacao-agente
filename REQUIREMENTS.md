# Requisitos

<!-- TOC -->
**Sumário**

- [O que é necessário](#o-que-é-necessário)
<!-- /TOC -->

Descubra o seu sistema e siga o arquivo correspondente:

```bash
make check-os        # mostra o sistema detectado e o arquivo de requisitos
make requirements    # imprime (e tenta abrir) esse arquivo
```

Sem `make`: `cat /etc/os-release && uname -m` (Ubuntu) ou `sw_vers && uname -m` (macOS).

| Sistema | Arquiteturas | Arquivo |
|---|---|---|
| Ubuntu 22.04 LTS | amd64, arm64 | [docs/requirements/REQUIREMENTS-ubuntu-22.04.md](docs/requirements/REQUIREMENTS-ubuntu-22.04.md) |
| Ubuntu 24.04 LTS | amd64, arm64 | [docs/requirements/REQUIREMENTS-ubuntu-24.04.md](docs/requirements/REQUIREMENTS-ubuntu-24.04.md) |
| Ubuntu 26.04 LTS | amd64, arm64 | [docs/requirements/REQUIREMENTS-ubuntu-26.04.md](docs/requirements/REQUIREMENTS-ubuntu-26.04.md) |
| macOS | Intel (amd64), Apple Silicon (arm64) | [docs/requirements/REQUIREMENTS-macos.md](docs/requirements/REQUIREMENTS-macos.md) |

## O que é necessário

- **Docker Engine** com **Docker Compose v2** e **Buildx**. No macOS, o runtime é o **Colima** com o Docker CLI.
- `make`, `git` e `curl`.
- **mise**, que instala no seu usuário as versões fixadas em [mise.toml](mise.toml): Python 3.12, uv e jq.
- Uma chave do Google AI Studio.

Sistemas fora da tabela não são suportados. `make check-os` falha neles; `SKIP_OS_CHECK=1` força a execução por sua conta e risco.
