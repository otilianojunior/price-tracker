import time

from src.config import config
from src.services.application_service import ApplicationService


class PriceTrackerScheduler:
    """Executa o Price Tracker em intervalos configuráveis."""

    def __init__(self):
        self.application_service = ApplicationService()
        self.interval_seconds = config.CHECK_INTERVAL_MINUTES * 60

    def run_once(self):
        """Executa uma única rodada."""
        return self.application_service.run()

    def run_forever(self):
        """Executa o Price Tracker continuamente."""
        print()
        print("=" * 60)
        print("PRICE TRACKER SCHEDULER")
        print("=" * 60)
        print(
            f"Intervalo entre rodadas: "
            f"{config.CHECK_INTERVAL_MINUTES} minutos"
        )
        print("Scheduler iniciado.")
        print("Pressione Ctrl+C para encerrar.")
        print("=" * 60)

        while True:
            inicio = time.monotonic()

            try:
                resultado = self.run_once()

                print()
                print("Resultado da rodada:")
                print(resultado)

            except KeyboardInterrupt:
                print()
                print("Scheduler encerrado pelo usuário.")
                break

            except Exception as erro:
                print()
                print(
                    "ERRO inesperado no Scheduler:"
                )
                print(erro)

            duracao = time.monotonic() - inicio
            espera = max(
                0,
                self.interval_seconds - duracao,
            )

            print()
            print(
                f"Próxima rodada em "
                f"{espera / 60:.1f} minutos."
            )

            try:
                time.sleep(espera)
            except KeyboardInterrupt:
                print()
                print("Scheduler encerrado pelo usuário.")
                break
