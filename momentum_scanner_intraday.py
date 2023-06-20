import time
import json
import pandas as pd
import dex_chain
from dex_chain import NETWORK_MAP_CG, NETWORK_MAP_CGTERMINAL, DEX_CHAIN
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


def add_intraday_rets(df, lag):
    df[f"{lag}H Return"] = {
        token: 100 * gecko.coin_return_intraday(token, lag) for token in df.index
    }


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
    fdv = pd.Series(
        {
            x["id"]: x["fully_diluted_valuation"]
            for x in gecko.query_coins_markets(df.index)
        }
    )
    df["fully_diluted_valuation"] = fdv


def get_risk_query(token, stoploss=0.05, profittaking=0.05):
    price = gecko.simple_price_1d([token])[token]["usd"]
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    print("enter at:", price, "stop-loss:", slprice, "profit-taking:", ptprice)
    return slprice, ptprice

def lookup(dex):
    """
    find the chain on which a dex is deployed
    """
    chain_cg = None
    chain_cgterminal = None
    for i in DEX_CHAIN:
        if i == dex:
            chain = DEX_CHAIN[i]
            chain_cg = NETWORK_MAP_CG[chain]
            chain_cgterminal = NETWORK_MAP_CGTERMINAL[chain]
    return chain_cg, chain_cgterminal

def get_cgterminal_url(chain, contract_addr):
    return 'https://api.geckoterminal.com/api/v2/networks/'+chain+'/tokens/'+contract_addr+'/pools'

def find_best_reserve(url):
    """
    find best reserve via cg-terminal api
    """
    reserve_data = requests.get(url).json()
    time.sleep(1) # to avoid hitting cgterminal endpoint's rate limit
    best_reserve = 0
    
    return max(data['attributes']['reserve_in_usd'] for data in reserve_data['data'])

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
    best_pair = ""
    best_reserve = 0
    re = gecko.query_coin(coin)
    for ticker in re["tickers"]:
        if ticker["market"]["identifier"] == dex:
            pair = ticker["target_coin_id"] + "<>" + ticker["coin_id"]
            volume = float(ticker["converted_volume"]["usd"])
            if volume > best_volume:
                best_pair = pair
                best_volume = volume

    chain_cg, chain_cgterminal = lookup(dex)
    if chain_cg in re['platforms']:
        contract_addr = re['platforms'][chain_cg]
        url = get_cgterminal_url(chain_cgterminal, contract_addr)
        best_reserve = find_best_reserve(url)

    return best_volume, best_pair, best_reserve


def add_best_liquidity(df, dex):
    for token in df.index:
        best_volume, best_pair,best_reserve = find_best_liquidity(token, dex)
        df.loc[token, "best_volume"] = best_volume
        df.loc[token, "best_pair"] = best_pair
        df.loc[token, "best_reserve"] = best_reserve


def get_high_returns(
    dex: str, lag_return: int, daily_volume: int, vol_30: int, market_cap: int
):
    vols = gecko.exchanges(dex)
    vols = metrics.filter_pairs(vols, volume=daily_volume)
    df = metrics.find_rets_24h(vols)
    df = add_volume_marketcap(df)
    df = df[
        (df["30_day_mean_volume"] >= vol_30)
        & (df["30_day_mean_marketcap"] >= market_cap)
    ]
    if df.empty:
        return df
    df = metrics.add_7drets(df)
    for lag in {6, 12, lag_return}:
        add_intraday_rets(df, lag)
    add_fdv(df)
    add_best_liquidity(df, dex)

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
    add_intraday_rets(df, lag)
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
