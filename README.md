# trading-bots

## DISCLAIMER: THIS IS OPEN SOURCE SOFTWARE WITHOUT ANY WARRANTY. PLEASE USE AT YOUR OWN RISK. NO GUARANTEES ARE GIVEN AND NOT OUTPUT HERE IS ENDORSED AS TRADING ADVICE. THIS REPO IS FOR EXPERIMENTAL AND RESEARCH PURPOSES ONLY.

## MomentumScanner
Python script used to scan a DEX's hottest coin based on returns and volume.

The script requires two libs: pandas, requests
```
$pip install pandas
$pip install requests
```
To use the script to scan a DEX: 
```
$python MomentumScanner.py DEXname
```

The script currently supports the following DEXname's:
```
pancakeswap_new, apeswap_bsc, uniswap_v2, mdex_bsc, biswap, babyswap, babydogeswap
```
