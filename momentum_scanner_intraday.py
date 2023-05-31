import time

import pandas as pd

import cache_db
import gecko
import metrics


def token_volume_marketcap(token):
    """
    Days = 100 to make sure we are getting daily values
    """
    df = gecko.market_chart(token, days=100)
    vol_30 = df["total_volumes"].iloc[-30:].mean()
    mc_30 = df["market_caps"].iloc[-30:].mean()
    return vol_30, mc_30

def token_fdv(token):
    token_info = gecko.query_coins_markets(token)
    fdv = token_info[0]["fully_diluted_valuation"]
    return fdv

def add_intraday_rets(df, lag):
    col_name = f"{lag}H Return"
    df[col_name] = None
    for i in df.index:
        intra_ret = gecko.coin_return_intraday(i, lag)
        df.loc[i, col_name] = intra_ret
    return df


def add_technical_indicators(df):
    col_name = "macd_ratio"
    df[col_name] = None
    for i in df.index:
        macd = metrics.token_technical_indicator(i)
        df.loc[i, col_name] = macd
    return df


def add_volume_marketcap(df):
    for token in df.index:
        vol_30, mc_30 = token_volume_marketcap(token)
        df.loc[token, "30_day_mean_volume"] = vol_30
        df.loc[token, "30_day_mean_marketcap"] = mc_30
    return df

def add_fdv(df):
    for token in df.index:
        df.loc[token, 'fully_diluted_valuation'] = token_fdv(token)
    return df

def get_risk_query(token, stoploss=0.05, profittaking=0.05):
    price = gecko.simple_price_1d([token])[token]["usd"]
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    print("enter at:", price, "stop-loss:", slprice, "profit-taking:", ptprice)
    return slprice, ptprice


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

def find_best_liquidity(coin, dex):
    best_volume = 0
    best_pair = ''
    for ticker in gecko.query_coin(coin)["tickers"]:
        if ticker["market"]["identifier"] == dex:
            pair = ticker["target_coin_id"] +  "<>" + ticker["coin_id"]
            volume = float(ticker["volume"])
            if volume > best_volume:
                best_pair = pair
                best_volume = volume

    return best_volume, best_pair

def add_best_liquidity(df, dex):
    for token in df.index:
        best_volume, best_pair = find_best_liquidity(token, dex)
        df.loc[token, 'best_volume'] = best_volume
        df.loc[token, 'best_pair'] = best_pair
    return df

def get_high_returns(
    dex: str, lag_return: int, daily_volume: int, vol_30: int, market_cap: int
):
    vols = gecko.exchanges(dex)
    lag_col = f"{lag_return}H Return"
    vols = metrics.filter_pairs(vols, volume=daily_volume)
    df = metrics.find_rets_24h(vols)
    df = add_volume_marketcap(df)
    df = df[
        (df["30_day_mean_volume"] >= vol_30)
        & (df["30_day_mean_marketcap"] >= market_cap)
    ]
    if df.empty:
        return df
    # df = df[df["24H Return"] >= 0] # dropping this line in case all tokens have negative returns
    df = metrics.add_7drets(df)
    df = add_intraday_rets(df, lag_return)
    df[lag_col] = df[lag_col].apply(lambda x: round(x * 100, 2))
    # df = df[df[lag_col] >= 0]
    df = df.sort_values(by=lag_col, ascending=False)
    df = add_fdv(df)
    df = add_best_liquidity(df, dex)

    return df


def required_pairs(dex):
    return pd.DataFrame(
        [(f"{a}<>{b}", 1e7) for a, b in cache_db.get_pairs(dex)],
        columns=("pair", "volume"),
    ).set_index("pair")


def find_best_return(dex, stoploss, profittaking, lag):
    lag_col = f"{lag}H Return"
    vols = gecko.exchanges(dex)
    if vols.empty:
        raise Exception("Query did not get any returned values")

    vols = metrics.filter_pairs(vols, volume=150000)
    if vols.empty:
        raise Exception("No pair found with enough volume")

    extras = required_pairs(dex)
    extras = extras[~extras.index.isin(vols.index)]
    vols = pd.concat([vols, extras])
    df = metrics.find_rets_24h(vols)
    # df = df.sort_values(by='24H Return',ascending=False)
    df = df[df["24H Return"] >= 0]
    df = metrics.add_7drets(df)
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
    enterprice, sl, pt = metrics.get_trades(str(hottoken), stoploss, profittaking)

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
