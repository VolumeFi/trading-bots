import datetime
import time

import pandas as pd

import cache_db
import gecko


def token_return_24h(token):
    prices = gecko.market_chart(token, days=1)
    open, close = prices["price"][0], prices["price"][-1]
    if open == 0:
        return 0
    return (close - open) / open


def token_return_intraday(token, lag):
    df = gecko.market_chart(token, days=1)
    current = df.index[-1]
    prback = df["price"].asof(current - datetime.timedelta(hours=lag))
    prcurrent = df["price"].iloc[-1]
    return (prcurrent - prback) / prback


def token_technical_indicator(token):
    df = gecko.market_chart(token, days=100)
    exp_short = df["price"].ewm(span=12, adjust=False).mean()
    exp_long = df["price"].ewm(span=26, adjust=False).mean()
    macd = (exp_short - exp_long) / exp_long
    return macd.iloc[-1]


def token_price(token):
    return gecko.market_chart(token, days=1)["price"][-1]


def token_volume_marketcap(token):
    """
    Days = 100 to make sure we are getting daily values
    """
    df = gecko.market_chart(token, days=100)
    vol_30 = df["total_volumes"].iloc[-30:].mean()
    mc_30 = df["market_caps"].iloc[-30:].mean()
    return vol_30, mc_30


def query_volumes(dex):
    dex_data = gecko.exchanges(dex)
    df = pd.DataFrame(
        [
            {
                "pair": ticker["coin_id"] + "<>" + ticker["target_coin_id"],
                "volume": ticker["converted_volume"]["usd"],
            }
            for ticker in dex_data
        ]
    )
    df.set_index("pair", inplace=True)
    df.index.name = "pair"
    return df


def filter_pairs(vols, *, volume=1e5):
    return vols[vols["volume"] >= volume]


def tokens_ret24h(tokens):
    query = gecko.simple_price_1d(tokens)
    ret24 = pd.DataFrame()
    for k in query:
        ret24.loc[k, "24H Return"] = query[k]["usd_24h_change"]
    return ret24


def add_7drets(df):
    df["7D Return"] = None
    for i in df.index:
        ret7d = gecko.query_coin(i)["market_data"]["price_change_percentage_7d"]
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
    main_tokens = {"binance-usd", "wbnb", "weth"}
    tokens = set(main_tokens)
    for pair in vols:
        toks = set(pair.split("<>")) - main_tokens
        if len(toks) == 1:
            tokens.update(toks)
    rets24h = tokens_ret24h(tokens)
    rets24h.index.name = "Token name"
    return rets24h


def add_volume_marketcap(df):
    for token in df.index:
        vol_30, mc_30 = token_volume_marketcap(token)
        df.loc[token, "30_day_mean_volume"] = vol_30
        df.loc[token, "30_day_mean_marketcap"] = mc_30
    return df


def get_risk(price, stoploss, profittaking):
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    return slprice, ptprice


def get_risk_query(token, stoploss=0.05, profittaking=0.05):
    price = gecko.simple_price_1d([token])[token]["usd"]
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    print("enter at:", price, "stop-loss:", slprice, "profit-taking:", ptprice)
    return slprice, ptprice


def get_trades(token, stoploss, profittaking):
    price = token_price(token)
    sl, pt = get_risk(price, stoploss, profittaking)
    return price, sl, pt


def find_liquidity(coin, dex):
    for ticker in gecko.query_coin(coin)["tickers"]:
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
        dex: str, lag_return: int, daily_volume: int, vol_30=100, market_cap=100
):
    vols = query_volumes(dex)
    lag_col = f"{lag_return}H Return"
    vols = filter_pairs(vols, volume=daily_volume)
    df = find_rets_24h(vols)
    df = add_volume_marketcap(df)
    df = df[
        (df["30_day_mean_volume"] >= vol_30)
        & (df["30_day_mean_marketcap"] >= market_cap)
        ]
    if df.empty:
        return df
    df = df[df["24H Return"] >= 0]
    df = add_7drets(df)
    df = add_intraday_rets(df, lag_return)
    df[lag_col] = df[lag_col].apply(lambda x: round(x * 100, 2))
    df = df[df[lag_col] >= 0]
    df = df.sort_values(by=lag_col, ascending=False)

    return df


def required_pairs(dex):
    return pd.DataFrame(
        [(f"{a}<>{b}", 1e7) for a, b in cache_db.get_pairs(dex)],
        columns=("pair", "volume"),
    ).set_index("pair")


def find_best_return(dex, stoploss, profittaking, lag):
    lag_col = f"{lag}H Return"
    vols = query_volumes(dex)
    if vols.empty:
        raise Exception("Query did not get any returned values")

    vols = filter_pairs(vols, volume=150000)
    if vols.empty:
        raise Exception("No pair found with enough volume")

    extras = required_pairs(dex)
    extras = extras[~extras.index.isin(vols.index)]
    vols = pd.concat([vols, extras])
    df = find_rets_24h(vols)
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
        print("Currently no token satisfies the filtering conditions")
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
