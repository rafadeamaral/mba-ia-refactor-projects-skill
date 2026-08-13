"""Serialização de produto — allowlist de campos expostos pela API."""

CAMPOS_PUBLICOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def produto_para_resposta(produto: dict) -> dict:
    return {campo: produto.get(campo) for campo in CAMPOS_PUBLICOS}


def produtos_para_resposta(produtos: list[dict]) -> list[dict]:
    return [produto_para_resposta(p) for p in produtos]
