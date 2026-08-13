"""Constantes de domínio — elimina os magic numbers e listas inline."""

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"

NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PEDIDO_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
STATUS_PEDIDO_INICIAL = "pendente"
STATUS_PEDIDO_APROVADO = "aprovado"
STATUS_PEDIDO_CANCELADO = "cancelado"

TIPO_USUARIO_PADRAO = "cliente"

# Faixas de desconto sobre o faturamento: (valor mínimo, alíquota), da maior para a menor.
FAIXAS_DESCONTO = (
    (10_000, 0.10),
    (5_000, 0.05),
    (1_000, 0.02),
)

PAGINACAO_LIMITE_PADRAO = 50
PAGINACAO_LIMITE_MAXIMO = 200
