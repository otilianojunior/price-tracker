from html import escape


class PublicationFormatter:
    """Formata promoções para publicação nos canais."""

    @staticmethod
    def format_telegram(
        promotion_data: dict,
        affiliate_url: str,
    ) -> str:
        """Formata a promoção usando HTML compatível com Telegram."""

        nome = escape(
            promotion_data["nome_produto"]
        )

        preco_atual = promotion_data["preco_atual"]
        preco_original = promotion_data["preco_original"]

        parcelas = promotion_data.get("parcelas")
        valor_parcela = promotion_data.get("valor_parcela")
        sem_juros = promotion_data.get("sem_juros")
        forma_pagamento = promotion_data.get("forma_pagamento")

        preco_atual_formatado = (
            f"R$ {float(preco_atual):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        preco_original_formatado = None

        if preco_original is not None:
            preco_original_formatado = (
                f"R$ {float(preco_original):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        parcelamento_formatado = None

        if (
            parcelas
            and valor_parcela is not None
        ):
            valor_parcela_formatado = (
                f"R$ {float(valor_parcela):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

            detalhes_pagamento = []

            if sem_juros:
                detalhes_pagamento.append("sem juros")

            if forma_pagamento == "cartao":
                detalhes_pagamento.append("no cartão")

            sufixo_pagamento = ""

            if detalhes_pagamento:
                sufixo_pagamento = (
                    " "
                    + " ".join(detalhes_pagamento)
                )

            parcelamento_formatado = (
                f"💳 {parcelas}x de "
                f"{valor_parcela_formatado}"
                f"{sufixo_pagamento}"
            )

        linhas = [
            f"🛍️ <b>{nome}</b>",
            "",
        ]

        if preco_original_formatado:
            linhas.append(
                f"💰 De: <s>{preco_original_formatado}</s>"
            )

        linhas.append(
            f"🔥 <b>Por: {preco_atual_formatado}</b>"
        )

        if parcelamento_formatado:
            linhas.append(
                parcelamento_formatado
            )

        linhas.extend(
            [
                "",
                "🛒 <b>Link do Produto:</b>",
                affiliate_url,
                "",
                "⏳ Preço sujeito a alteração.",
            ]
        )

        return "\n".join(linhas)
