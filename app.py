import bottle
from bottle import request

import momentum_scanner_intraday


##sentry_sdk.init(
##    dsn="https://955ac0a74d244e2c914767a351d4d069@o1200162.ingest.sentry.io/4505082653573120",
##    traces_sample_rate=1.0,
##)


@bottle.post("/get_high_returns")
def get_high_returns():
    dex, lag_return, daily_volume = (
        request.json["dex"],
        request.json["lag_return"],
        request.json["daily_volume"],
    )
    if "market_cap" in request.json().keys() or "vol_30" in request.json().keys():
        market_cap, vol_30 = (request.json["market_cap"], request.json["vol_30"])
        df = momentum_scanner_intraday.get_high_returns(
            dex, lag_return, daily_volume, vol_30, market_cap
        )
    else:
        df = momentum_scanner_intraday.get_high_returns(dex, lag_return, daily_volume)
    df.dropna(how="all", axis=1, inplace=True)
    return df.to_dict()


def main():
    bottle.run(host="localhost", port=8080)


if __name__ == "__main__":
    main()
