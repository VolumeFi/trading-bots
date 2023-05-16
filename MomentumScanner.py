import sys
import time

import gecko
import metrics


def findliquidity(coin, dex):
    re = gecko.query_coin(coin)
    for ticker in re.json()["tickers"]:
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


def findbestreturn(dex, stoploss, profittaking, neg7D):
    vols = gecko.exchanges(dex)
    if len(vols) != 0:
        vols1 = metrics.filter_pairs(vols, volume=150000)
        if len(vols1) == 0:
            print("No pair found with enough volume")
            return
        else:
            vols1 = vols1  # .iloc[1:]
    else:
        print("Endpoint issues, query did not get any returned values")
        return

    rets24h = metrics.find_rets_24h(vols1)
    rets24h = rets24h.sort_values(by="24H Return", ascending=False)
    rets24h = rets24h[rets24h["24H Return"] >= 0]
    rets24h = metrics.add_7drets(rets24h)
    #    rets24h['24H Return'] = rets24h['24H Return'].apply(lambda x: str(round(x*100,2))+'%')
    rets24h["24H Return"] = rets24h["24H Return"].apply(
        lambda x: str(round(x, 2)) + "%"
    )
    if neg7D:
        rets24h = rets24h[rets24h["7D Return"] < 0]
        if len(rets24h) == 0:
            print("No hot tokens with negative 7D return")
            return

    try:
        rets24h["7D Return"] = rets24h["7D Return"].apply(
            lambda x: str(round(x, 2)) + "%"
        )
    except:
        pass

    hottoken = rets24h.index[0]
    time.sleep(1)
    enterprice, sl, pt = metrics.get_trades(str(hottoken), stoploss, profittaking)

    print(dex, " top winners: ", flush=True)
    print(rets24h, flush=True)
    print("* * * * *", flush=True)
    print("Hottest token in the past 24H: ", flush=True)
    print(hottoken, ", 24H return: ", rets24h["24H Return"].iloc[0], flush=True)
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
    # findbestreturn(dex='apeswap_bsc', stoploss=0.05, profittaking=0.05)
    args = sys.argv

    if "neg7D" in args:
        neg7D = True
        args.remove("neg7D")
    else:
        neg7D = False

    if len(args) == 1:
        findbestreturn(
            dex="pancakeswap_new", stoploss=0.05, profittaking=0.05, neg7D=neg7D
        )
    elif len(args) == 2:
        findbestreturn(
            dex=str(sys.argv[1]), stoploss=0.05, profittaking=0.05, neg7D=neg7D
        )
