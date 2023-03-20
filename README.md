# trading-bots

## MomentumScanner
Python script used to scan a DEX's hottest coin based on returns and volume.

The script requires two libs: pandas, requests
```
$pip install pandas
$pip install requests
```
To use the script to scan a DEX: 
```
from MomentumScanner import findbestreturn
print(findbestreturn('DEX NAME'))
```

You can also run a test scan on ApeSwap and Pancakeswap on BSC:
```
$python MomentumScanner.py
```
