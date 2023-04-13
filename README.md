# trading-bots

## DISCLAIMER: THIS IS OPEN SOURCE SOFTWARE WITHOUT ANY WARRANTY. PLEASE USE AT YOUR OWN RISK. NO GUARANTEES ARE GIVEN AND NOT OUTPUT HERE IS ENDORSED AS TRADING ADVICE. THIS REPO IS FOR EXPERIMENTAL AND RESEARCH PURPOSES ONLY.

## MomentumScanner
Python script used to scan a DEX's hottest coin based on returns and volume.

The script requires two libs: pandas, requests
```
$pip install pandas
$pip install requests
```
To use the script to scan a DEX and rank by 24H returns: 
```
$python MomentumScanner.py DEX
```
Scan intraday returns for a DEX and rank by integer hours:
```
$python MomentumScanner_intraday.py DEX Hours
```
Hours is an integer between 1 and 23. 

Calculate technical indicator (currently available INDICATOR_NAME: MACD_ratio, RSI) for a DEX:
```
$python MomentumScanner_techindicator.py DEX INDICATOR_NAME 
```

The script currently supports the all DEXes on CoinGecko. Check all ids in
```
https://api.coingecko.com/api/v3/exchanges
```
