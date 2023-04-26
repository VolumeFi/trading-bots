import datetime
import os
import sys
import time

import pandas as pd
import requests

APIROOT = "https://pro-api.coingecko.com/api/v3"
CG_PARAM = "x_cg_pro_api_key"
CG_KEY = os.environ["CG_KEY"]


def conv_dt_rev(dt_int):
    """
    convert datetime format
    """
    return datetime.datetime(1970, 1, 1, 0, 0, 0) + datetime.timedelta(
        seconds=int(dt_int) / 1e3
    )


def parse_price(pr):
    df = pd.DataFrame()
    for i in pr:
        dt_ = conv_dt_rev(i[0])
        pr_ = i[1]
        df.loc[dt_, "price"] = pr_
    return df


def query_dex(dex):
    return requests.get(
        f"{APIROOT}/exchanges/{dex}", params={CG_PARAM: CG_KEY}, timeout=10
    ).json()["tickers"]


def query_token_price(token, *, days):
    return requests.get(
        f"{APIROOT}/coins/{token}/market_chart",
        params={"vs_currency": "usd", "days": days, CG_PARAM: CG_KEY},
        timeout=10,
    ).json()["prices"]


def query_coin(coin):
    return requests.get(
        f"{APIROOT}/coins/{coin}", params={CG_PARAM: CG_KEY}, timeout=10
    ).json()


def token_return_24h(token):
    prices = query_token_price(token, days=1)

    open, close = prices[0][1], prices[-1][1]

    if open == 0:
        return 0
    return (close - open) / open


def token_return_intraday(token, lag):
    pr = query_token_price(token, days=1)
    df = parse_price(pr)
    df = df.sort_index()
    current = df.index[-1]
    prback = df["price"].asof(current - datetime.timedelta(hours=lag))
    prcurrent = df["price"].iloc[-1]
    return (prcurrent - prback) / prback


def token_technical_indicator(token):
    pr = query_token_price(token, days=100)
    df = parse_price(pr)
    df = df.sort_index()
    exp_short = df["price"].ewm(span=12, adjust=False).mean()
    exp_long = df["price"].ewm(span=26, adjust=False).mean()
    macd = (exp_short - exp_long) / exp_long
    return macd.iloc[-1]


def token_price(token):
    prices = query_token_price(token, days=1)
    return prices[-1][1]


def query_volumes(dex):
    dex_data = query_dex(dex)

    vols = pd.Series(dtype=float)
    for i in dex_data:
        id_ = i["coin_id"] + "<>" + i["target_coin_id"]
        vols.loc[id_] = i["converted_volume"]["usd"]

    return vols.sort_values(ascending=False)


def filter_pairs(vols, volume=1e5):
    vols = vols[vols >= volume]
    return vols


def find_token(pair):
    a = pair.split("<>")
    if a[0] in ["wbnb", "binance-usd", "weth"]:
        return a[1]
    else:
        return a[0]


def query_tokens_price1d(tokens):
    return requests.get(
        f"{APIROOT}/simple/price",
        params={
            "ids": ",".join(tokens),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            CG_PARAM: CG_KEY,
        },
    ).json()


def tokens_ret24h(tokens):
    query = query_tokens_price1d(tokens)
    ret24 = pd.DataFrame()
    for k in query:
        ret24.loc[k, "24H Return"] = query[k]["usd_24h_change"]
    return ret24


def add_7drets(df):
    df["7D Return"] = None
    for i in df.index:
        ret7d = query_coin(i)["market_data"]["price_change_percentage_7d"]
        df.loc[i, "7D Return"] = ret7d
    return df


def add_intraday_rets(df, lag):
    col_name = f"{lag}H Return"
    df[col_name] = None
    for i in df.index:
        intra_ret = token_return_intraday(i, lag)
        df.loc[i, col_name] = intra_ret
    return df


def add_technical_indicators(df):
    col_name = "macd_ratio"
    df[col_name] = None
    for i in df.index:
        macd = token_technical_indicator(i)
        df.loc[i, col_name] = macd
    return df


def find_rets_24h(vols):
    tokens = set()
    for pair in vols.index:
        if "wbnb" in pair or "binance-usd" in pair or "weth" in pair:
            tokens.add(find_token(pair))
    rets24h = tokens_ret24h(tokens)
    rets24h.index.name = "Token name"
    return rets24h


def get_risk(price, stoploss, profittaking):
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    return slprice, ptprice


def get_risk_query(token, stoploss=0.05, profittaking=0.05):
    price = query_tokens_price1d([token])[token]["usd"]
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    print("enter at:", price, "stop-loss:", slprice, "profit-taking:", ptprice)
    return slprice, ptprice


def get_trades(token, stoploss, profittaking):
    price = token_price(token)
    sl, pt = get_risk(price, stoploss, profittaking)
    return price, sl, pt


def find_liquidity(coin, dex):
    for ticker in query_coin(coin)["tickers"]:
        if ticker["market"]["identifier"] == dex:
            # print('DEX: ',ticker['market']['identifier'],ticker['volume'])
            print(
                "DEX: ",
                ticker["market"]["identifier"],
                ", Pair: ",
                ticker["target_coin_id"],
                "<>",
                ticker["coin_id"],
                ", Volume: ",
                ticker["volume"],
            )


def get_high_returns(
    dex: str, lag_return: int, daily_volume: int, _monthly_mean_volume, _liquidity
):
    vols = query_volumes(dex)
    lag_col = f"{lag_return}H Return"
    df = pd.DataFrame()
    if len(vols) != 0:
        vols1 = filter_pairs(vols, volume=daily_volume)
        if len(vols1) > 0:
            df = find_rets_24h(vols1)
            if len(df) == 0:
                return df
            df = df[df["24H Return"] >= 0]
            df = add_7drets(df)
            df = add_intraday_rets(df, lag_return)
            df[lag_col] = df[lag_col].apply(lambda x: round(x * 100, 2))
            df = df[df[lag_col] >= 0]
            df = df.sort_values(by=lag_col, ascending=False)
    return df


def find_best_return(dex, stoploss, profittaking, lag):
    lag_col = f"{lag}H Return"
    vols = query_volumes(dex)
    if len(vols) != 0:
        vols1 = filter_pairs(vols, volume=150000)
        if len(vols1) == 0:
            print("No pair found with enough volume")
            return
        else:
            vols1 = vols1  # .iloc[1:]
    else:
        print("Endpoint issues, query did not get any returned values")
        return

    df = find_rets_24h(vols1)
    # df = df.sort_values(by='24H Return',ascending=False)
    df = df[df["24H Return"] >= 0]
    df = add_7drets(df)
    df = add_intraday_rets(df, lag)
    # df = add_technical_indicators(df)
    df = df.sort_values(by=lag_col, ascending=False)

    df["24H Return"] = df["24H Return"].apply(lambda x: str(round(x, 2)) + "%")
    try:
        df["7D Return"] = df["7D Return"].apply(lambda x: str(round(x, 2)) + "%")
        df[lag_col] = df[lag_col].apply(lambda x: str(round(x * 100, 2)) + "%")
    except Exception:
        pass

    if len(df) == 0:
        print('Currently no token satisfies the filtering conditions')
        return

    hottoken = df.index[0]
    time.sleep(1)
    enterprice, sl, pt = get_trades(str(hottoken), stoploss, profittaking)

    print(dex, " top winners: ", flush=True)
    print(df, flush=True)
    print("* * * * *", flush=True)
    print("Hottest token in the past " + str(lag) + "H: ", flush=True)
    print(hottoken, lag_col, ": ", df[lag_col].iloc[0], flush=True)
    if enterprice != 0:
        print("Enter at: ", enterprice, flush=True)
        print(
            "Stop-loss at: ", sl, " (stop loss percentage: ", stoploss, ")", flush=True
        )
        print(
            "Profit-taking at: ",
            pt,
            " (profit taking percentage: ",
            profittaking,
            ")",
            flush=True,
        )
    else:
        print(
            "Enter price, stop-loss and profit-taking calculation failed due to endpoint issue",
            flush=True,
        )
    print("* * * * *", flush=True)
    print("liquidity profile: ", flush=True)
    find_liquidity(hottoken, dex)
    print("----------------------------------------------", flush=True)


if __name__ == "__main__":
    #    findbestreturn(dex='pancakeswap_new', stoploss=0.05, profittaking=0.05,lag=6)

    args = sys.argv
    lag = int(args[-1])

    if len(args) == 2:
        find_best_return(
            dex="pancakeswap_new", stoploss=0.05, profittaking=0.05, lag=lag
        )
    elif len(args) == 3:
        find_best_return(
            dex=str(sys.argv[1]), stoploss=0.05, profittaking=0.05, lag=lag
        )
