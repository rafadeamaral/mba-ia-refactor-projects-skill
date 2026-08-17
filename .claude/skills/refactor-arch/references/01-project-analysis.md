# Referência 1 — Análise de Projeto (Fase 1)

Heurísticas para detectar stack, persistência, domínio e arquitetura real de uma codebase desconhecida.
Ordem de confiança: **manifesto de dependências > imports do código > extensão de arquivo > nome de pasta**.

---

## 1. Detecção de linguagem e gerenciador de pacotes

Procure na raiz (e um nível abaixo) por arquivos-manifesto. A presença do manifesto é o sinal forte; a
contagem de extensões só desempata.

| Manifesto | Linguagem | Como ler a versão |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python | `python_requires`, `[project] requires-python`, ou `python --version` |
| `package.json` | JavaScript / TypeScript | campo `engines.node`; TS se houver `tsconfig.json` |
| `go.mod` | Go | diretiva `go 1.x` |
| `pom.xml`, `build.gradle` | Java / Kotlin | `<maven.compiler.source>`, `sourceCompatibility` |
| `Gemfile` | Ruby | `ruby '3.x'` |
| `composer.json` | PHP | `require.php` |
| `*.csproj`, `*.sln` | C# / .NET | `<TargetFramework>` |
| `Cargo.toml` | Rust | `edition` |

Sem manifesto: conte arquivos por extensão ignorando diretórios de dependência e artefatos
(`node_modules`, `venv`, `.venv`, `__pycache__`, `vendor`, `dist`, `build`, `target`, `.git`).

## 2. Detecção de framework web

Confirme sempre com o manifesto **e** com um import real no código — um pacote listado e nunca importado
é dívida, não arquitetura (registre como achado `QUAL-07`).

| Sinal no manifesto | Sinal no código | Framework |
|---|---|---|
| `flask` | `from flask import Flask` | Flask |
| `fastapi` | `from fastapi import FastAPI` | FastAPI |
| `django` | `INSTALLED_APPS`, `urls.py`, `manage.py` | Django |
| `express` | `require('express')`, `import express` | Express |
| `@nestjs/core` | `@Module`, `@Controller` | NestJS |
| `koa`, `fastify`, `hapi` | `new Koa()`, `fastify()` | Koa / Fastify / Hapi |
| `spring-boot-starter-web` | `@RestController` | Spring Boot |
| `rails` | `config/routes.rb` | Ruby on Rails |
| `laravel/framework` | `routes/web.php`, `Illuminate\` | Laravel |
| `gin-gonic/gin`, `net/http` | `gin.Default()`, `http.HandleFunc` | Gin / stdlib |

**Sem framework web?** Pode ser CLI, worker, biblioteca ou script. O alvo MVC ainda se aplica, mas a
camada "View" vira a interface de entrada (comandos de CLI, consumidores de fila). Ajuste a proposta e
diga isso explicitamente.

## 3. Detecção de persistência

Duas perguntas: **qual banco** e **com ou sem ORM**. A resposta muda todo o plano da Fase 3.

| Sinal | Persistência |
|---|---|
| `import sqlite3`, `require('sqlite3')`, `better-sqlite3`, `*.db` na raiz | SQLite direto |
| `psycopg2`, `pg`, `mysql2`, `pymysql` | PostgreSQL / MySQL direto |
| `flask_sqlalchemy`, `sqlalchemy`, `db.Model` | SQLAlchemy |
| `sequelize`, `typeorm`, `prisma`, `mongoose`, `drizzle` | ORM/ODM Node |
| `django.db.models`, `ActiveRecord`, `Eloquent`, `Hibernate` | ORM do framework |
| `redis`, `pymongo`, `MongoClient` | NoSQL / cache |

**Mapear as tabelas/entidades:**

- Sem ORM: procure `CREATE TABLE` no código e nos arquivos `.sql`; procure também `INSERT INTO`,
  `FROM <tabela>` e `UPDATE <tabela>` para pegar tabelas criadas fora do repositório.
- Com ORM: procure declarações de model (`class X(db.Model)`, `sequelize.define`, `@Entity`,
  `schema.prisma`) e leia `__tablename__` / `tableName`.
- Registre também **onde** o schema é criado. Schema criado dentro de uma função de acesso a dados ou no
  import do módulo é achado (`ARCH-07`).

## 4. Inferência do domínio

Combine três fontes e escreva **uma frase**:

1. Nomes de tabelas/entidades (`produtos`, `pedidos`, `itens_pedido` → e-commerce; `courses`,
   `enrollments`, `payments` → plataforma de cursos; `tasks`, `categories` → gerenciador de tarefas).
2. Prefixos de rota (`/api/checkout`, `/relatorios/vendas`, `/tasks`).
3. `README` do projeto e strings de resposta da rota raiz.

Formato: `<tipo de aplicação> (<entidades principais>)`. Ex.: `API de E-commerce (produtos, pedidos, usuários)`.

## 5. Inventário de endpoints — o contrato a preservar

Este é o artefato mais importante da Fase 1: é contra ele que a Fase 3 será validada. Precisa ser
**completo**, incluindo rotas registradas fora do padrão principal.

Padrões de registro de rota por stack:

| Stack | Sinais a procurar |
|---|---|
| Flask | `@app.route`, `@bp.route`, `app.add_url_rule(...)`, `Blueprint(`, `register_blueprint` |
| FastAPI | `@app.get/post/put/delete`, `@router.*`, `include_router` |
| Django | `path(`, `re_path(`, `urlpatterns` |
| Express | `app.get/post/put/delete/patch/use`, `router.*`, `Router()`, métodos que recebem `app` |
| NestJS | `@Get`, `@Post`, `@Controller` |
| Spring | `@GetMapping`, `@RequestMapping` |

> **Armadilha comum:** rotas registradas por `add_url_rule` ou por um método de classe
> (`manager.setupRoutes(app)`) não aparecem se você procurar só por decoradores. Faça a busca por
> **todos** os padrões da stack antes de fechar o inventário.

Monte a tabela:

| Método | Path | Handler atual (`arquivo:linha`) | Observação |
|---|---|---|---|

Marque com destaque endpoints administrativos, destrutivos ou sem autenticação — eles serão findings na
Fase 2.

## 6. Mapeamento da arquitetura real

**Regra central: pasta não é camada.** Um projeto com `models/`, `routes/` e `services/` pode violar MVC
completamente. Classifique pelo que o código **faz**, não pelo nome do arquivo.

Para cada arquivo-fonte, marque quais responsabilidades ele contém:

| Responsabilidade | Como reconhecer |
|---|---|
| **Roteamento** | registro de rota, parsing de path/query params |
| **HTTP I/O** | acesso a `request`/`req`, montagem de `response`, códigos de status |
| **Validação** | checagem de campos obrigatórios, tamanhos, formatos, valores permitidos |
| **Regra de negócio** | cálculos, decisões condicionais sobre o domínio, orquestração de passos |
| **Acesso a dados** | SQL, chamadas de ORM, transações |
| **Apresentação** | montagem de dicionário/DTO de saída, formatação de data e número |
| **Infraestrutura** | conexão, DDL, seed, envio de e-mail, chamada a gateway externo |
| **Configuração** | segredos, hosts, portas, flags |

Um arquivo com 4+ responsabilidades é candidato a **God Class/Module** (`ARCH-01`).

### Classificação da arquitetura de partida

Isso define o quanto a Fase 3 vai transformar:

| Nível | Descrição | Estratégia da Fase 3 |
|---|---|---|
| **A — Monolito plano** | 1–5 arquivos na raiz, tudo misturado | Criar todas as camadas do zero |
| **B — Separação nominal** | Existem pastas de camada, mas responsabilidades vazam entre elas | Realocar responsabilidade, manter a árvore quando fizer sentido |
| **C — MVC parcial** | Camadas corretas, faltam middlewares/config/validação | Completar camadas faltantes e corrigir pontos |
| **D — MVC adequado** | Estrutura correta | Só correções pontuais; **não** reestruture por reestruturar |

Registre também **tamanho**: número de arquivos-fonte e total de linhas (útil para dimensionar o esforço e
para o cabeçalho do relatório).

## 7. Checklist de saída da Fase 1

- [ ] Linguagem e versão detectadas a partir do manifesto
- [ ] Framework e versão detectados e confirmados por import real
- [ ] Banco, ORM (ou ausência) e tabelas mapeados
- [ ] Domínio descrito em uma frase
- [ ] **Todos** os endpoints inventariados, incluindo os registrados fora do padrão principal
- [ ] Contagem de arquivos-fonte e linhas (excluindo dependências)
- [ ] Nível de arquitetura de partida classificado (A/B/C/D)
- [ ] Nenhum arquivo foi modificado
