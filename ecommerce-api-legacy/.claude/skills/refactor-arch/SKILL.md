---
name: refactor-arch
description: Analisa, audita e refatora uma codebase para o padrão MVC, de forma agnóstica de linguagem e framework. Use quando o usuário pedir para refatorar a arquitetura de um projeto, auditar anti-patterns e code smells, avaliar violações de MVC/SOLID, gerar relatório de auditoria arquitetural, ou reestruturar código legado em camadas (models, views/routes, controllers). Executa em 3 fases — análise, auditoria com relatório e confirmação humana, e refatoração validada.
---

# Refatoração Arquitetural para MVC

Skill de três fases que transforma um projeto legado em uma aplicação organizada no padrão MVC,
**sem alterar o comportamento externo da API**.

## Princípios inegociáveis

1. **Nada é modificado antes da confirmação humana.** As Fases 1 e 2 são estritamente somente-leitura.
   Nenhum `Write`, `Edit`, `mv`, `rm` ou comando que altere arquivos antes do usuário aprovar a Fase 3.
2. **Comportamento preservado.** Todo endpoint que respondia antes deve responder depois, com o mesmo
   método, path, código de status e formato de resposta. Refatoração não é reescrita de funcionalidade.
3. **Evidência, não suposição.** Todo achado do relatório cita `arquivo:linha` verificados por leitura
   direta do código. Se não conseguir citar a linha, o achado não entra no relatório.
4. **Adaptação ao ponto de partida.** Um monolito de 4 arquivos e um projeto que já tem `models/` e
   `routes/` exigem transformações diferentes. Detecte o que já existe antes de propor estrutura.
5. **Segurança tem precedência.** Achados CRITICAL de segurança são corrigidos na Fase 3 mesmo quando a
   correção é pequena perto da reestruturação.

## Arquivos de referência

Carregue sob demanda, na fase correspondente. Não leia todos de uma vez.

| Arquivo | Quando ler |
|---|---|
| `references/01-project-analysis.md` | Fase 1 — heurísticas de detecção de stack, banco, domínio e arquitetura |
| `references/02-antipattern-catalog.md` | Fase 2 — catálogo de 38 anti-patterns com sinais de detecção e severidade |
| `references/03-audit-report-template.md` | Fase 2 — formato obrigatório do relatório |
| `references/04-mvc-architecture.md` | Fase 3 — regras do alvo MVC e responsabilidade de cada camada |
| `references/05-refactoring-playbook.md` | Fase 3 — 19 padrões de transformação com exemplos antes/depois |

---

## FASE 1 — Análise do projeto

**Objetivo:** entender o que o projeto é antes de julgá-lo. Somente leitura.

Leia `references/01-project-analysis.md` e execute:

1. **Detectar a stack** — linguagem, framework e versão, dependências relevantes, gerenciador de pacotes.
   Use os arquivos-manifesto (`requirements.txt`, `package.json`, `pyproject.toml`, `go.mod`, `pom.xml`,
   `Gemfile`, `composer.json`) como fonte primária e os imports do código como confirmação.
2. **Mapear a persistência** — tipo de banco, ORM (ou ausência dele), tabelas/entidades e onde o schema
   é definido.
3. **Inferir o domínio** — o que a aplicação faz, em uma frase, a partir dos nomes de rota, entidades e
   tabelas.
4. **Inventariar a superfície pública** — liste **todos** os endpoints (método + path + handler). Esta
   lista é o contrato que a Fase 3 tem obrigação de preservar.
5. **Mapear a arquitetura atual** — quantos arquivos-fonte, quantas linhas, quais camadas existem de fato
   (não por nome de pasta) e onde cada responsabilidade mora hoje.

Ignore `node_modules/`, `venv/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `.git/` e arquivos de lock
na contagem de arquivos-fonte.

**Saída obrigatória** — imprima exatamente neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão quando detectável>
Framework:     <framework + versão>
Dependencies:  <dependências relevantes, separadas por vírgula>
Domain:        <domínio em uma frase>
Architecture:  <descrição da organização atual em uma frase>
Source files:  <N> files analyzed | ~<N> lines of code
Persistence:   <banco + ORM ou "SQL direto">
DB tables:     <tabelas detectadas>
Endpoints:     <N> endpoints mapeados
================================
```

Em seguida, imprima a tabela de endpoints (método, path, handler atual). Não comente qualidade do código
nesta fase — a Fase 1 descreve, não julga.

---

## FASE 2 — Auditoria de arquitetura

**Objetivo:** produzir um relatório de achados acionável. Ainda somente leitura.

Leia `references/02-antipattern-catalog.md` e `references/03-audit-report-template.md` e execute:

1. **Cruze cada arquivo-fonte contra o catálogo.** Para cada anti-pattern, procure os sinais de detecção
   listados. Use `Grep` para os sinais que têm padrão textual e leitura completa do arquivo para os
   estruturais (God Class, camada nominal, lógica de negócio fora do lugar).
2. **Registre cada ocorrência com `arquivo:linha` exatos.** Quando o mesmo anti-pattern aparece em muitos
   pontos, agrupe em um único finding e liste as linhas — não infle a contagem.
3. **Classifique a severidade** pela tabela do catálogo, ajustando pelo contexto real (ex.: SQL Injection
   em rota autenticada de admin ainda é CRITICAL; `print()` como log é LOW mesmo em 20 lugares).
4. **Verifique APIs deprecated obrigatoriamente** — seção `DEP-*` do catálogo. Confirme a versão da
   linguagem/framework no manifesto antes de classificar algo como deprecated, e sempre indique o
   equivalente moderno.
5. **Ordene por severidade** (CRITICAL → HIGH → MEDIUM → LOW) e, dentro da mesma severidade, por impacto.
6. **Escreva o relatório** no formato de `references/03-audit-report-template.md`, imprima no terminal e
   salve em `reports/audit-<nome-do-projeto>.md` (criando `reports/` se necessário — este é o único
   arquivo que a Fase 2 pode escrever).
7. **Monte o plano de refatoração**: a estrutura de diretórios proposta e o mapeamento
   `finding → transformação do playbook`.

**Metas de qualidade da auditoria:** mínimo de 5 findings e pelo menos 1 CRITICAL ou HIGH em qualquer
projeto real. Se encontrou menos que isso, a varredura foi superficial — releia os arquivos maiores
integralmente antes de concluir.

**Portão de confirmação — obrigatório.** Depois de imprimir o relatório e o plano, **pare**. Pergunte ao
usuário se deve prosseguir (use `AskUserQuestion` quando disponível, senão imprima o prompt abaixo) e
encerre o turno aguardando a resposta. Não encadeie a Fase 3 na mesma execução.

```
================================
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Se a resposta for negativa, encerre sem modificar nada e informe onde o relatório foi salvo.

---

## FASE 3 — Refatoração para MVC

**Objetivo:** reestruturar o projeto eliminando os achados, sem quebrar nada.

Leia `references/04-mvc-architecture.md` e `references/05-refactoring-playbook.md`.

### 3.0 — Capturar o baseline (antes de qualquer alteração)

Não é possível provar que nada quebrou sem saber como o sistema respondia antes.

1. Suba a aplicação original e registre, para cada endpoint do inventário da Fase 1, o **status code** e o
   **formato da resposta** (chaves do JSON). Salve em um arquivo de trabalho temporário.
2. Se a aplicação não sobe no estado original, registre isso explicitamente e use o inventário de rotas
   como contrato de referência.
3. Derrube o processo antes de editar arquivos.

### 3.1 — Executar as transformações

Aplique os padrões do playbook na ordem abaixo. A ordem importa: cada passo depende do anterior.

1. **Configuração** — extrair segredos e parâmetros para um módulo de config alimentado por variáveis de
   ambiente; criar `.env.example`; nunca versionar valores reais. *(RF-01)*
2. **Camada de dados** — criar `models/` por domínio, com queries parametrizadas e acesso ao banco
   isolado; um arquivo por entidade. *(RF-02, RF-05, RF-08)*
3. **Camada de negócio** — mover regras de negócio para `controllers/` (ou `services/` quando o projeto
   já usa essa nomenclatura); controllers não conhecem `request`/`response` mais do que o necessário e
   não montam SQL. *(RF-06, RF-15)*
4. **Camada de roteamento** — criar `views/` ou `routes/` com Blueprints/Routers por domínio; handlers
   finos que só traduzem HTTP ↔ chamada de controller. *(RF-07)*
5. **Validação** — extrair as validações duplicadas para schemas/validators reutilizados por
   criação e atualização. *(RF-13)*
6. **Middlewares** — error handler centralizado, exceções de domínio, logging estruturado, CORS restrito.
   *(RF-09, RF-18)*
7. **Correções pontuais** — transações, N+1, paginação, integridade referencial, APIs deprecated,
   constantes nomeadas, remoção de código morto. *(RF-10, RF-11, RF-12, RF-16, RF-17)*
8. **Composition root** — `app.py`/`app.js` reduzido a montagem: criar app, carregar config, registrar
   blueprints e middlewares. Sem regra de negócio, sem SQL, sem rota inline. *(RF-08)*

Regras durante a execução:

- **Remova o que é indefensável**, não o refatore: endpoints de execução de SQL arbitrário, endpoints
  destrutivos sem autenticação e credenciais versionadas saem. Registre a remoção no relatório final.
- **Elimine código morto** identificado na auditoria (helpers, serviços e métodos nunca chamados) — ou
  passe a usá-lo, se ele for a implementação correta que as rotas duplicaram.
- **Preserve nomes de endpoint, payloads e códigos de status.** Mudança de contrato só é aceitável para
  remover vazamento de dado sensível (ex.: parar de devolver senha) — e deve ser destacada na saída.
- **Atualize os arquivos auxiliares** que apontam para caminhos antigos (`requirements.txt`,
  `package.json` `main`/`scripts`, `seed.py`, `README` do projeto, `.gitignore` para `.env`).

### 3.2 — Validar

Validação é obrigatória e precisa de evidência real de execução. Rode e mostre a saída:

1. **Import/parse** — a aplicação carrega sem erro de sintaxe ou import quebrado.
2. **Boot** — o servidor sobe e fica ouvindo na porta esperada.
3. **Endpoints** — exercite **todos** os endpoints do inventário da Fase 1 e compare status e formato com
   o baseline de 3.0. Inclua ao menos um caminho de erro (404 e 400).
4. **Anti-patterns residuais** — reexecute os greps dos findings CRITICAL/HIGH e confirme que zeraram.

Se algo falhar, corrija e revalide. Não declare sucesso com teste vermelho — reporte o que ficou quebrado.

**Saída obrigatória:**

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios resultante>

## Findings Resolved
CRITICAL: <n>/<n> | HIGH: <n>/<n> | MEDIUM: <n>/<n> | LOW: <n>/<n>

## Validation
  <✓|✗> Application boots without errors
  <✓|✗> All <N> endpoints respond (status + shape iguais ao baseline)
  <✓|✗> Error paths return 400/404 corretamente
  <✓|✗> Zero CRITICAL/HIGH anti-patterns remaining

## Breaking Changes
<lista, ou "Nenhuma — contrato da API preservado">
================================
```
