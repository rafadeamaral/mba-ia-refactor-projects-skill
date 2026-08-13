"""Validação de produto — as mesmas regras para criação e atualização.

Na versão anterior o bloco era copiado entre `criar_produto` e `atualizar_produto` e já havia
divergido: só a criação validava tamanho de nome e categoria. Um único validador elimina a
divergência.
"""
from src.constants import (
    CATEGORIA_PADRAO,
    CATEGORIAS_VALIDAS,
    NOME_PRODUTO_MAX,
    NOME_PRODUTO_MIN,
)
from src.middlewares.exceptions import ValidationError
from src.validators.common import exigir_corpo

CAMPOS_OBRIGATORIOS = (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque"))


def validar(dados) -> dict:
    dados = exigir_corpo(dados)

    for campo, rotulo in CAMPOS_OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")

    preco = _numero(dados["preco"], "Preço")
    estoque = _numero(dados["estoque"], "Estoque")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")

    nome = str(dados["nome"])
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")

    categoria = dados.get("categoria", CATEGORIA_PADRAO)
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(f"Categoria inválida. Válidas: {list(CATEGORIAS_VALIDAS)}")

    return {
        "nome": nome,
        "descricao": dados.get("descricao", ""),
        "preco": preco,
        "estoque": int(estoque),
        "categoria": categoria,
    }


def _numero(valor, rotulo: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValidationError(f"{rotulo} deve ser numérico")
    return float(valor)
