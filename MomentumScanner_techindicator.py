import sys
import time

import gecko
import metrics
import MomentumScanner


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


def get_sma(prices, length):
    return prices.rolling(length).mean()


def get_bollinger_bands_last(prices, length):
    sma = get_sma(prices, length)
    std = prices.rolling(length).std()
    bollinger_up = sma + std * 2  # Calculate top band
    bollinger_down = sma - std * 2  # Calculate bottom band
    return bollinger_up.iloc[-1], bollinger_down.iloc[-1]


def token_technical_indicator_bollingerband_updiff(token):
    df = gecko.market_chart(token, days=100)
    bollinger_up, bollinger_down = get_bollinger_bands_last(df["price"], length=7)
    bb_updiff = df["price"].iloc[-1] - bollinger_down
    bb_updiff = bb_updiff / df["price"].iloc[-1]

    return bb_updiff


def add_technical_indicators(df, col_name):
    # col_name = 'MACD_ratio'
    df[col_name] = None
    for i in df.index:
        try:
            if col_name == "MACD_ratio":
                indicator = metrics.token_technical_indicator_macd(i)
            elif col_name == "RSI":
                indicator = token_technical_indicator_rsi(i)
            elif col_name == "BB_updiff":
                indicator = token_technical_indicator_bollingerband_updiff(i)
            df.loc[i, col_name] = indicator
            # time.sleep(0.01)
        except:
            df.loc[i, col_name] = None
    return df


def getriskquery(token, stoploss=0.05, profittaking=0.05):
    re = gecko.simple_price_1d([token])
    price = re.json()[token]["usd"]
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    print("enter at:", price, "stop-loss:", slprice, "profit-taking:", ptprice)
    return slprice, ptprice


def findbestreturn(dex, stoploss, profittaking, col_name):
    vols = gecko.exchanges(dex)
    if len(vols) != 0:
        vols = metrics.filter_pairs(vols, volume=150000)
        if len(vols) == 0:
            print("No pair found with enough volume")
            return
        else:
            vols1 = vols  # .iloc[1:]
    else:
        print("Endpoint issues, query did not get any returned values")
        return

    if vols.empty:
        print("Currently no token satisfies the filtering conditions")
        return

    df = metrics.find_rets_24h(vols1)
    techindicator_col = col_name
    df = add_technical_indicators(df, col_name)
    df = df[df[techindicator_col] > 0]
    df = df.sort_values(by=techindicator_col, ascending=False)

    hottoken = df.index[0]
    time.sleep(1)
    enterprice, sl, pt = metrics.get_trades(str(hottoken), stoploss, profittaking)

    print(dex, " top winners: ", flush=True)
    print(df[[techindicator_col]], flush=True)
    print("* * * * *", flush=True)
    print("Hottest token: ", flush=True)
    print(hottoken, flush=True)
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
    MomentumScanner.findliquidity(hottoken, dex)
    print("----------------------------------------------", flush=True)


if __name__ == "__main__":
    #    findbestreturn(dex='pancakeswap_new', stoploss=0.05, profittaking=0.05,lag=6)

    args = sys.argv
    col_name = args[-1]

    if len(args) == 2:
        findbestreturn(
            dex="pancakeswap_new", stoploss=0.05, profittaking=0.05, col_name=col_name
        )
    elif len(args) == 3:
        findbestreturn(
            dex=str(sys.argv[1]), stoploss=0.05, profittaking=0.05, col_name=col_name
        )
