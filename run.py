from src.scheduler.scheduler import PriceTrackerScheduler


if __name__ == "__main__":
    scheduler = PriceTrackerScheduler()
    scheduler.run_forever()
