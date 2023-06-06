import itertools
import json
import logging
import os

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
        return SESSION.get(
            url,
            params={**params, "x_cg_pro_api_key": CG_KEY},
            timeout=10,
        ).json()

    return cache_db.try_cache(path, params, fetch)


def exchanges(dex):
    data = []
    for page in range(1, 2):
        tickers = get("exchanges", dex, "tickers", params={"page": page})["tickers"]
        if not tickers:
            break
        data.extend(
            {
                "pair": ticker["coin_id"] + "<>" + ticker["target_coin_id"],
                "volume": ticker["converted_volume"]["usd"],
            }
            for ticker in tickers
            if not ticker["is_stale"]
        )
    df = pd.DataFrame(data)
    df.set_index("pair", inplace=True)
    df.index.name = "pair"
    return df


def market_chart(coin, *, days):
    assert days in (1, 100)
    chart = get(
        "coins", coin, "market_chart", params={"vs_currency": "usd", "days": days}
    )
    if chart == {"error": "coin not found"}:
        logging.info("coin not found for %s", coin)
        chart = {
            "prices": [],
            "market_caps": [],
            "total_volumes": [],
        }
    pr = pd.DataFrame(chart["prices"], columns=["ts", "price"])
    mc = pd.DataFrame(chart["market_caps"], columns=["ts", "market_caps"])
    tv = pd.DataFrame(chart["total_volumes"], columns=["ts", "total_volumes"])
    for df in [pr, mc, tv]:
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
    df = pd.concat([pr, mc, tv], axis=1)
    return df


def coin_return_intraday(coin, lag):
    df = market_chart(coin, days=1)
    current = df.index[-1]
    prback = df["price"].asof(current - pd.Timedelta(hours=lag))
    prcurrent = df["price"].iloc[-1]
    return (prcurrent - prback) / prback


def price(coin):
    return market_chart(coin, days=1)["price"][-1]


def query_coin(coin):
    return get("coins", coin)


def query_coins_markets(coins):
    return get(
        "coins",
        "markets",
        params={
            "ids": ",".join(sorted(coins)),
            "vs_currency": "usd",
        },
    )


def simple_price_1d(coins):
    coins = sorted(coins)
    prices = {}
    for batch in batched(coins, 100):
        prices |= get(
            "simple",
            "price",
            params={
                "ids": ",".join(sorted(batch)),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
        )
    return prices


def batched(iterable, n):
    "Batch data into tuples of length n. The last batch may be shorter."
    # TODO: This is added to itertools in python 3.12
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while batch := tuple(itertools.islice(it, n)):
        yield batch
