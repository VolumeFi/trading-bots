from MomentumScanner_intraday import gethighreturns
from sys import argv
import json


dex = str(argv[1])
lag_return = int(argv[2])
daily_volume = int(argv[3])
monthly_mean_volume = argv[4]
liquidity = argv[5]

df = gethighreturns(dex, lag_return, daily_volume, monthly_mean_volume, liquidity)

if len(df) > 0:
    output = df.to_json()
else:
    output = {}

print(output)

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=4)