import webbrowser

from src.auth.mercado_livre import MercadoLivreAuth


def main():
    auth = MercadoLivreAuth()

    authorization_url, state = auth.get_authorization_url()

    print("Abra a URL abaixo para autorizar o aplicativo:")
    print()
    print(authorization_url)
    print()

    webbrowser.open(authorization_url)

    code = input("Cole aqui o authorization code: ").strip()
    returned_state = input("Cole aqui o state recebido: ").strip()

    if not code:
        raise ValueError("Authorization code não informado.")

    if not returned_state:
        raise ValueError("State não informado.")

    if returned_state != state:
        raise ValueError(
            "State inválido. A resposta não corresponde "
            "à solicitação iniciada pela aplicação."
        )

    tokens = auth.exchange_code_for_token(code)

    print()
    print("Autenticação concluída com sucesso.")
    print(
        f"Token expira em: "
        f"{tokens.get('expires_in')} segundos."
    )


if __name__ == "__main__":
    main()