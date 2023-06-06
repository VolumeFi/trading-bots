import json
import logging
import threading

import bottle
import sentry_sdk
from bottle import request

import cache_db
import gecko
import momentum_scanner_intraday

sentry_sdk.init(
    dsn="https://955ac0a74d244e2c914767a351d4d069@o1200162.ingest.sentry.io/4505082653573120",
    traces_sample_rate=1.0,
)


@bottle.post("/get_high_returns")
def get_high_returns():
    dex = request.json["dex"]
    lag_return = int(request.json["lag_return"])
    daily_volume = int(request.json["daily_volume"])
    market_cap = int(request.json.get("market_cap", 100))
    vol_30 = int(request.json.get("vol_30", 100))
    with cache_db.connect():
        df = momentum_scanner_intraday.get_high_returns(
            dex, lag_return, daily_volume, vol_30, market_cap
        )
    df.dropna(how="all", axis=1, inplace=True)
    df.fillna(0, inplace=True)
    return json.dumps(df.to_dict(), sort_keys=True)


def main():
    logging.basicConfig(level=logging.INFO)
    cache_db.init()
    gecko.init()
    threading.Thread(target=cache_db.warm_cache_loop).start()
    bottle.run(host="localhost", port=8080)


if __name__ == "__main__":
    main()
