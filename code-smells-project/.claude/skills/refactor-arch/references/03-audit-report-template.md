# Referência 3 — Template do Relatório de Auditoria (Fase 2)

Formato obrigatório da saída da Fase 2. O relatório é impresso no terminal **e** salvo em
`reports/audit-<nome-do-projeto>.md`.

## Regras de formatação

1. **Ordem fixa:** CRITICAL → HIGH → MEDIUM → LOW. Dentro da mesma severidade, maior impacto primeiro.
2. **Numeração sequencial** dos findings (`#1`, `#2`, …), atribuída após a ordenação — o número reflete a
   prioridade de correção.
3. **Todo finding cita `arquivo:linha`.** Múltiplas ocorrências: liste as linhas separadas por vírgula,
   use `a-b` para intervalos e `(+N ocorrências)` quando passar de oito.
4. **Quatro campos obrigatórios por finding:** `File`, `Description`, `Impact`, `Recommendation`.
   - `Description` — o que o código faz, factualmente. Sem adjetivos.
   - `Impact` — a consequência concreta (o que quebra, o que vaza, quantas queries a mais).
   - `Recommendation` — a ação, referenciando o padrão do playbook (`RF-xx`).
5. **Nunca invente linha.** Sem localização verificada, o achado não entra.
6. **Sem duplicata:** o mesmo anti-pattern no mesmo arquivo é **um** finding com várias linhas.
7. **Idioma:** cabeçalhos e rótulos em inglês (conforme o template); prosa em português.

---

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório do projeto>
Stack:   <linguagem + framework>
Files:   <N> analyzed | ~<N> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

<Um parágrafo (2–4 frases) com o diagnóstico arquitetural: qual é o problema estrutural central,
não a lista de sintomas.>

## Findings

### #1 [CRITICAL] <Nome do anti-pattern> (<ID do catálogo>)
File: <caminho:linha(s)>
Description: <o que o código faz>
Impact: <consequência concreta>
Recommendation: <ação> (RF-xx)

### #2 [CRITICAL] <...>
...

### #N [LOW] <...>
...

## Deprecated APIs
| API | Local | Deprecated desde | Equivalente moderno |
|---|---|---|---|
| <...> | <arquivo:linha> | <versão> | <...> |

<Ou: "Nenhuma API deprecated detectada para <linguagem X.Y> / <framework Z>.">

## Refactoring Plan

### Estrutura proposta
```
<árvore de diretórios alvo>
```

### Mapeamento finding → transformação
| Finding | Transformação | Arquivos afetados |
|---|---|---|
| #1 | RF-xx <nome> | <...> |

### Contrato preservado
<N> endpoints inventariados na Fase 1 devem responder com o mesmo método, path, status e formato
após a refatoração. Mudanças de contrato previstas: <lista, ou "nenhuma">.

### Fora de escopo
<O que a refatoração não vai resolver e por quê — ex.: implementar JWT de verdade é feature, não
refatoração; migração de banco; troca de dependência sem aprovação.>

================================
Total: <N> findings
================================
````

---

## Exemplo preenchido (trecho)

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-08-13

## Summary
CRITICAL: 6 | HIGH: 4 | MEDIUM: 5 | LOW: 3

O projeto tem nomenclatura MVC sem separação real: `models.py` acumula acesso a dados de quatro
domínios, regras de negócio e formatação de resposta, enquanto a conexão vive em uma global de módulo.
A ausência de fronteira entre camadas é a causa direta dos achados de segurança — não há um ponto
único onde validar entrada, parametrizar query ou filtrar o que sai na resposta.

## Findings

### #1 [CRITICAL] SQL Injection por concatenação (SEC-02)
File: models.py:28,47-50,57-61,68,92,109-111,126-129,140,148-166 (+8 ocorrências)
Description: Todas as queries são montadas concatenando parâmetros diretamente na string SQL. Em
`login_usuario` (models.py:109-111) o e-mail e a senha entram sem escape na cláusula WHERE.
Impact: `email = "' OR '1'='1' --"` autentica como o primeiro usuário da tabela, que é o admin semeado
em database.py:76. Pela rota de busca (models.py:289-297) é possível extrair qualquer tabela.
Recommendation: Substituir toda concatenação por queries parametrizadas com placeholders `?` na camada
de models (RF-02).

### #2 [CRITICAL] Endpoint de execução de SQL arbitrário (SEC-05)
File: app.py:59-78
Description: `POST /admin/query` recebe `{"sql": "..."}` do corpo e executa direto no cursor, sem
autenticação nem allowlist.
Impact: Backdoor completo de banco exposto em `host="0.0.0.0"` — permite DROP TABLE, leitura da tabela
de usuários com senhas e escrita arbitrária.
Recommendation: Remover o endpoint. Não há versão segura de um executor de SQL exposto (RF-19).

### #7 [HIGH] God Module (ARCH-01)
File: models.py:1-314
Description: Um arquivo concentra acesso a dados de 4 domínios, regras de negócio (faixas de desconto
em 256-262, cálculo de total e baixa de estoque em 133-169) e montagem do DTO de resposta (12-21,
31-40, 304-313).
Impact: Impossível testar a regra de desconto sem um SQLite real; qualquer mudança de schema quebra a
serialização da API. É a origem dos findings #11 e #12.
Recommendation: Dividir em `models/` por domínio, mover regras para `controllers/` e extrair a
serialização para DTOs (RF-05, RF-06, RF-04).

## Deprecated APIs
| API | Local | Deprecated desde | Equivalente moderno |
|---|---|---|---|
| — | — | — | Nenhuma detectada para Python 3.x / Flask 3.1.1 |
````

---

## Erros comuns a evitar

| Erro | Correção |
|---|---|
| "O código está desorganizado" | Nomear o anti-pattern, o arquivo e a linha |
| Um finding por ocorrência do mesmo problema | Agrupar por anti-pattern + arquivo |
| Severidade inflada para engordar a lista | Aplicar a tabela; `print()` como log é LOW |
| `Impact` repetindo `Description` | `Impact` responde "e daí?" com consequência concreta |
| `Recommendation` genérica ("melhorar isso") | Ação + referência `RF-xx` |
| Relatório sem seção de deprecated | Sempre incluir, mesmo que para declarar ausência |
| Prosseguir para a Fase 3 sem confirmação | Parar após o relatório e aguardar resposta |
