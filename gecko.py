import json
import logging
import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry

import cache_db

API_ROOT = "https://pro-api.coingecko.com/api/v3"
CG_KEY = os.environ["CG_KEY"]

SESSION: requests.Session = None


def init():
    global SESSION
    SESSION = requests.Session()
    SESSION.mount(
        "http://",
        HTTPAdapter(
            max_retries=Retry(
                total=5,
                backoff_factor=0.1,
            )
        ),
    )


def get(*args, params: dict = {}):
    path = "/".join(args)

    def fetch():
        url = "/".join((API_ROOT, path))
        logging.info("%s %s", url, json.dumps(params))
        SESSION.get(
            url,
            params={**params, "x_cg_pro_api_key": CG_KEY},
            timeout=10,
        ).json()

    return cache_db.try_cache(path, params, fetch)


def exchanges(dex):
    data = [
        {
            "pair": ticker["coin_id"] + "<>" + ticker["target_coin_id"],
            "volume": ticker["converted_volume"]["usd"],
        }
        for ticker in get("exchanges", dex)["tickers"]
    ]
    df = pd.DataFrame(data)
    df.set_index("pair", inplace=True)
    df.index.name = "pair"
    return df


def exchanges_multi(dex, n_item=2):
    df = exchanges(dex)
    if n_item > 1:
        for i in range(n_item):
            tmp_df = exchanges(dex)
            for j in tmp_df.index:
                if j not in df.index:
                    df.loc[j, "volume"] = tmp_df.loc[j, "volume"]

    return df


def millis_to_datetime(dt_int):
    """
    Convert millis-since-epoch to a datetime.
    """
    return datetime(1970, 1, 1, 0, 0, 0) + timedelta(seconds=int(dt_int) / 1e3)


def market_chart(coin, *, days):
    assert days in (1, 100)
    chart = get(
        "coins", coin, "market_chart", params={"vs_currency": "usd", "days": days}
    )
    if chart == {"error": "coin not found"}:
        logging.info("coin not found for %s")
        chart = {
            "prices": [],
            "market_caps": [],
            "total_volumes": [],
        }
    prices = [(millis_to_datetime(dt), pr) for dt, pr in chart["prices"]]
    market_caps = [(millis_to_datetime(dt), mc) for dt, mc in chart["market_caps"]]
    total_volumes = [(millis_to_datetime(dt), tv) for dt, tv in chart["total_volumes"]]
    pr = pd.DataFrame(prices, columns=["ts", "price"]).set_index("ts")
    mc = pd.DataFrame(market_caps, columns=["ts", "market_caps"]).set_index("ts")
    tv = pd.DataFrame(total_volumes, columns=["ts", "total_volumes"]).set_index("ts")
    df = pd.concat([pr, mc, tv], axis=1)
    return df


def coin_return_intraday(coin, lag):
    df = market_chart(coin, days=1)
    current = df.index[-1]
    prback = df["price"].asof(current - timedelta(hours=lag))
    prcurrent = df["price"].iloc[-1]
    return (prcurrent - prback) / prback


def price(coin):
    return market_chart(coin, days=1)["price"][-1]


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
