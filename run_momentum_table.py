import json

import bottle
from bottle import request

import cache_db
import momentum_scanner_intraday


@bottle.post("/get_high_returns")
def get_high_returns():
    dex, lag_return, daily_volume = request.json["dex"], request.json["lag_return"], request.json["daily_volume"]

    def recompute():
        df = momentum_scanner_intraday.get_high_returns(
            dex, lag_return, daily_volume
        )
        df.dropna(how="all", axis=1, inplace=True)
        return df.to_json()

    return json.loads(
        cache_db.fetch((get_high_returns.__name__, dex, lag_return, daily_volume),
                       recompute)
    )


def main():
    bottle.run(host='localhost', port=8080)


if __name__ == "__main__":
    main()
