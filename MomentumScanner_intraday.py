import asyncio
import datetime
import os
import sys
import time

import aiohttp
import pandas as pd
import requests

APIROOT = "https://pro-api.coingecko.com/api/v3"
APIKEY = f"x_cg_pro_api_key={os.environ['CG_KEY']}"


def conv_dt_rev(dt_int):
    """
    convert datetime format
    """
    return datetime.datetime(1970, 1, 1, 0, 0, 0) + datetime.timedelta(
        seconds=int(dt_int) / 1e3
    )


def parse_price(pr):
    index = [conv_dt_rev(p[0]) for p in pr]
    data = [p[1] for p in pr]
    return pd.DataFrame(data, index=index, columns=["price"])


async def fetch(session, url):
    try:
        async with session.get(url=url, timeout=10) as response:
            js = await response.json()
        return js
    except Exception as e:
        # Janky scrubbing.
        url = url.replace(APIKEY, "x_cg_pro_api_key=XXX")
        print(f"Failed to fetch {url}: {e.__class__}")


def querydex(dex):
    try:
        return requests.get(f"{APIROOT}/exchanges/{dex}?{APIKEY}", timeout=10)
    except:
        print("timed out")


async def _query_token_prices(tokens, *, days):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1000)) as session:
        prices = await asyncio.gather(
            *[
                fetch(
                    session,
                    f"{APIROOT}/coins/{token}/market_chart?vs_currency=usd&days={days}&{APIKEY}",
                )
                for token in tokens
            ]
        )
    return prices


def query_token_prices(tokens, *, days):
    return asyncio.run(_query_token_prices(tokens, days=days))


async def _query_coins(coins):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1000)) as session:
        coins = await asyncio.gather(
            *[fetch(session, f"{APIROOT}/coins/{coin}?{APIKEY}") for coin in coins]
        )
    return coins


def query_coins(coins):
    return asyncio.run(_query_coins(coins))


def tokenreturn24h(token):
    js = query_token_prices([token], days=1)[0]
    try:
        prices = js["prices"]
    except:
        return 0

    closeprice = prices[-1][1]
    openprice = prices[0][1]

    if openprice == 0:
        return 0
    else:
        ret24h = (closeprice - openprice) / openprice
        return ret24h


def tokenreturn_intraday(tokens, lag):
    def parse_token_return(pr):
        try:
            pr = pr["prices"]

            df = parse_price(pr)
            df = df.sort_index()
            current = df.index[-1]
            prback = df["price"].asof(current - datetime.timedelta(hours=lag))
            prcurrent = df["price"].iloc[-1]
            ret = (prcurrent - prback) / prback

            return ret
        except Exception as e:
            print(e)
            return 0

    return list(map(parse_token_return, query_token_prices(tokens, days=1)))


def token_technical_indicator(token):
    pr = query_token_prices([token], days=100)[0]
    try:
        pr = pr["prices"]

        df = parse_price(pr)
        df = df.sort_index()
        exp_short = df["price"].ewm(span=12, adjust=False).mean()
        exp_long = df["price"].ewm(span=26, adjust=False).mean()
        macd = (exp_short - exp_long) / exp_long

        return macd.iloc[-1]
    except Exception as e:
        print(e)
        return 0


def tokenprice(token):
    js = query_token_prices([token], days=1)[0]
    try:
        prices = js["prices"]
    except:
        return 0

    price = prices[-1][1]
    return price


def queryvolumes(dex):
    query = querydex(dex)
    try:
        dexdata = query.json()["tickers"]
    except:
        return pd.DataFrame()

    vols = pd.Series(dtype=float)
    for i in dexdata:
        id_ = i["coin_id"] + "<>" + i["target_coin_id"]
        vols.loc[id_] = i["converted_volume"]["usd"]

    return vols.sort_values(ascending=False)


def filterpairs(vols, volume=1e5):
    vols = vols[vols >= volume]
    return vols


def findtoken(pair):
    a = pair.split("<>")
    if a[0] in ["wbnb", "binance-usd", "weth"]:
        return a[1]
    else:
        return a[0]


def querytokens_price1d(tokens):
    tokens = "%2C".join(tokens)
    try:
        return requests.get(
            f"{APIROOT}/simple/price?ids={tokens}&vs_currencies=usd&include_24hr_change=true&{APIKEY}",
            timeout=10,
        )
    except:
        print("timed out")


def tokens_ret24h(tokens):
    query = querytokens_price1d(tokens)
    ret24 = pd.DataFrame()
    try:
        q = query.json()
        for k in q.keys():
            ret24.loc[k, "24H Return"] = q[k]["usd_24h_change"]
    except Exception as e:
        print("error:", e)
        pass
    return ret24


def add_7drets(df):
    df["7D Return"] = [
        coin["market_data"]["price_change_percentage_7d"]
        for coin in query_coins(df.index)
    ]
    return df


def add_intraday_rets(df, lag):
    df[f"{lag}H Return"] = tokenreturn_intraday(df.index, lag)
    return df


def add_technical_indicators(df):
    col_name = "macd_ratio"
    df[col_name] = None
    for i in df.index:
        try:
            macd = token_technical_indicator(i)
            df.loc[i, col_name] = macd
            # time.sleep(0.01)
        except:
            df.loc[i, col_name] = None
    return df


def findrets24h(vols):
    tokens = []
    for pair in vols.index:
        if "wbnb" in pair or "binance-usd" in pair or "weth" in pair:
            token = findtoken(pair)
            if token not in tokens:
                tokens.append(token)
    rets24h = tokens_ret24h(tokens)
    rets24h.index.name = "Token name"
    return rets24h


def getrisk(price, stoploss, profittaking):
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    return slprice, ptprice


def getriskquery(token, stoploss=0.05, profittaking=0.05):
    re = querytokens_price1d([token])
    try:
        price = re.json()[token]["usd"]
        slprice = price * (1 - stoploss)
        ptprice = price * (1 + profittaking)
        print("enter at:", price, "stop-loss:", slprice, "profit-taking:", ptprice)
        # return slprice, ptprice
    except:
        print("query failed, try again shortly")


def gettrades(token, stoploss, profittaking):
    price = tokenprice(token)
    sl, pt = getrisk(price, stoploss, profittaking)
    return price, sl, pt


def findliquidity(coin, dex):
    re = query_coins([coin])[0]
    for ticker in re["tickers"]:
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


def gethighreturns(dex, lag_return, daily_volume, monthly_mean_volume, liquidity):
    vols = queryvolumes(dex)
    lag_col = f"{lag_return}H Return"
    df = pd.DataFrame()
    if len(vols) != 0:
        vols1 = filterpairs(vols, volume=daily_volume)
        if len(vols1) > 0:
            df = findrets24h(vols1)
            df = df[df["24H Return"] >= 0]
            df = add_7drets(df)
            df = add_intraday_rets(df, lag_return)
            df[lag_col] = df[lag_col].apply(lambda x: round(x * 100, 2))
            df = df[df[lag_col] >= 0]
            df = df.sort_values(by=lag_col, ascending=False)
    return df


def findbestreturn(dex, stoploss, profittaking, lag):
    lag_col = str(lag) + "H Return"
    vols = queryvolumes(dex)
    if len(vols) != 0:
        vols1 = filterpairs(vols, volume=150000)
        if len(vols1) == 0:
            print("No pair found with enough volume")
            return
        else:
            vols1 = vols1  # .iloc[1:]
    else:
        print("Endpoint issues, query did not get any returned values")
        return

    df = findrets24h(vols1)
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
    except:
        pass

    hottoken = df.index[0]
    time.sleep(1)
    enterprice, sl, pt = gettrades(str(hottoken), stoploss, profittaking)

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
    findliquidity(hottoken, dex)
    print("----------------------------------------------", flush=True)


if __name__ == "__main__":
    #    findbestreturn(dex='pancakeswap_new', stoploss=0.05, profittaking=0.05,lag=6)

    args = sys.argv
    lag = int(args[-1])

    if len(args) == 2:
        findbestreturn(dex="pancakeswap_new", stoploss=0.05, profittaking=0.05, lag=lag)
    elif len(args) == 3:
        findbestreturn(dex=str(sys.argv[1]), stoploss=0.05, profittaking=0.05, lag=lag)
