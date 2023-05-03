from sys import argv

import cache_db
from momentum_scanner_intraday import get_high_returns


##sentry_sdk.init(
##    dsn="https://955ac0a74d244e2c914767a351d4d069@o1200162.ingest.sentry.io/4505082653573120",
##    traces_sample_rate=1.0,
##)


def main():
    dex = argv[1]
    lag_return = int(argv[2])
    daily_volume = int(argv[3])

    def recompute():
        df = get_high_returns(dex, lag_return, daily_volume)
        df.dropna(how="all", axis=1, inplace=True)
        return df.to_json()

    output = cache_db.fetch(dex, lag_return, daily_volume, recompute)
    print(output)


if __name__ == "__main__":
    main()
