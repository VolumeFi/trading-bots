from sys import argv

import cache_db
from momentum_scanner_intraday import get_high_returns


def main():
    dex = argv[1]
    lag_return = int(argv[2])
    daily_volume = int(argv[3])
    monthly_mean_volume = argv[4]
    liquidity = argv[5]

    def recompute():
        df = get_high_returns(
            dex, lag_return, daily_volume, monthly_mean_volume, liquidity
        )
        df.dropna(how="all", axis=1, inplace=True)
        return df.to_json()

    output = cache_db.fetch(
        f"get_high_returns({dex}, {lag_return}, {daily_volume}, {monthly_mean_volume}, {liquidity})",
        recompute,
    )

    print(output)
    with open("data.json", "w", encoding="utf-8") as f:
        f.write(output)


if __name__ == "__main__":
    main()
