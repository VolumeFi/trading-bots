import os

import requests

import cache_db

API_ROOT = "https://pro-api.coingecko.com/api/v3"
CG_KEY = os.environ["CG_KEY"]


def get(*args, params: dict = {}):
    path = "/".join(args)
    f = lambda: requests.get(
        "/".join((API_ROOT, path)),
        params={**params, "x_cg_pro_api_key": CG_KEY},
        timeout=10,
    ).json()
    return cache_db.try_cache(path, params, f)


def exchanges(dex):
    return get("exchanges", dex)["tickers"]


def millis_to_datetime(dt_int):
    """
    Convert millis-since-epoch to a datetime.
    """
    from datetime import datetime, timedelta

    return datetime(1970, 1, 1, 0, 0, 0) + timedelta(seconds=int(dt_int) / 1e3)


def market_chart(coin, *, days):
    import pandas as pd

    chart = get(
        "coins", coin, "market_chart", params={"vs_currency": "usd", "days": days}
    )
    prices = [(millis_to_datetime(dt), pr) for dt, pr in chart["prices"]]
    return pd.DataFrame(prices, columns=["ts", "price"]).set_index("ts")


def query_coin(coin):
    return get("coins", coin)


def simple_price_1d(coins):
    return get(
        "simple",
        "price",
        params={
            "ids": ",".join(sorted(coins)),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
    )
