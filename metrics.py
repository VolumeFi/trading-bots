import pandas as pd

import gecko


def filter_pairs(vols, volume=1e5):
    return vols[vols["volume"] >= volume]


def get_risk(price, stoploss, profittaking):
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    return slprice, ptprice


def get_trades(token, stoploss, profittaking):
    price = gecko.price(token)
    sl, pt = get_risk(price, stoploss, profittaking)
    return price, sl, pt


def token_return_24h(token):
    prices = gecko.market_chart(token, days=1)
    open, close = prices["price"][0], prices["price"][-1]
    if open == 0:
        return 0
    return (close - open) / open


def tokens_ret24h(tokens):
    query = gecko.simple_price_1d(tokens)
    ret24 = pd.DataFrame()
    for k in query:
        ret24.loc[k, "24H Return"] = query[k]["usd_24h_change"]
    return ret24


def token_technical_indicator_macd(token):
    df = gecko.market_chart(token, days=100)
    exp_short = df["price"].ewm(span=12, adjust=False).mean()
    exp_long = df["price"].ewm(span=26, adjust=False).mean()
    macd = (exp_short - exp_long) / exp_long
    return macd.iloc[-1]


def token_technical_indicator_rsi(token):
    df = gecko.market_chart(token, days=100)
    prdiff = df["price"].diff().dropna()
    prdiffpos = prdiff[prdiff >= 0]
    prdiffneg = prdiff[prdiff < 0]

    if len(prdiffpos) > 0:
        gain_ema = prdiffpos.ewm(span=12, adjust=False).mean().iloc[-1]
    else:
        gain_ema = 0
    if len(prdiffneg) > 0:
        loss_ema = prdiffneg.ewm(span=12, adjust=False).mean().iloc[-1]
    else:
        loss_ema = 1
    rs = gain_ema / loss_ema
    rsi = 100 - (100 / (1 + rs))

    return rsi


def token_technical_indicator(token):
    df = gecko.market_chart(token, days=100)
    indicators = {}
    exp_short = df["price"].ewm(span=12, adjust=False).mean()
    exp_long = df["price"].ewm(span=26, adjust=False).mean()
    macd = (exp_short - exp_long) / exp_long
    indicators["macd_ratio"] = macd.iloc[-1]

    prdiff = df["price"].diff().dropna()
    prdiffpos = prdiff[prdiff >= 0]
    prdiffneg = prdiff[prdiff < 0]

    if len(prdiffpos) > 0:
        gain_ema = prdiffpos.ewm(span=12, adjust=False).mean().iloc[-1]
    else:
        gain_ema = 0
    if len(prdiffneg) > 0:
        loss_ema = prdiffneg.ewm(span=12, adjust=False).mean().iloc[-1]
    else:
        loss_ema = 1
    rs = gain_ema / loss_ema
    rsi = 100 - (100 / (1 + rs))
    indicators["rsi"] = rsi
    return indicators


def find_rets_24h(vols):
    main_tokens = {"binance-usd", "wbnb", "weth"}
    tokens = set(main_tokens)
    for pair in vols.index:
        toks = set(pair.split("<>")) - main_tokens
        if len(toks) == 1:
            tokens.update(toks)
    rets24h = tokens_ret24h(tokens)
    rets24h.index.name = "Token name"
    return rets24h


def add_7drets(df):
    df["7D Return"] = None
    for i in df.index:
        ret7d = gecko.query_coin(i)["market_data"]["price_change_percentage_7d"]
        df.loc[i, "7D Return"] = ret7d
    return df
