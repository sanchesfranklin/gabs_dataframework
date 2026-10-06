"""Caminhos das camadas do lakehouse (arquitetura medalhão).

Cada camada é um bucket. Dentro dele, a organização é produto/tabela:

    s3a://bronze/vendas/pedidos
          ^^^^^^ ^^^^^^ ^^^^^^^
          camada produto tabela

    landing -> arquivo como veio da fonte (JSON, CSV...), sem alteração
    bronze  -> o mesmo dado em tabela Delta, sem regra de negócio
    silver  -> limpo, tipado, padronizado e sem duplicatas
    gold    -> agregado e modelado para consumo
"""

LAYERS = ("landing", "bronze", "silver", "gold")


def path(layer: str, product: str, table: str | None = None) -> str:
    """Monta o caminho de uma tabela (ou da pasta do produto) em uma camada.

    >>> path("bronze", "vendas", "pedidos")
    's3a://bronze/vendas/pedidos'
    >>> path("landing", "vendas")
    's3a://landing/vendas'
    """
    if layer not in LAYERS:
        raise ValueError(f"Camada inválida: {layer!r}. Use uma de {LAYERS}.")

    parts = [product] if table is None else [product, table]
    for part in parts:
        if not part or "/" in part:
            raise ValueError(f"Nome inválido: {part!r}. Não pode ser vazio nem conter '/'.")

    return f"s3a://{layer}/" + "/".join(parts)
