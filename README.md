# trading-bots

## DISCLAIMER: THIS IS OPEN SOURCE SOFTWARE WITHOUT ANY WARRANTY. PLEASE USE AT YOUR OWN RISK. NO GUARANTEES ARE GIVEN AND NOT OUTPUT HERE IS ENDORSED AS TRADING ADVICE. THIS REPO IS FOR EXPERIMENTAL AND RESEARCH PURPOSES ONLY.

## Momentum Scanner
Python script used to scan a DEX's hottest coin based on returns and volume.

### Set up
You need to have a CoinGecko API Key, set as an environment variable `CG_KEY`. 

### Instruction
1. Use the script to scan a DEX and rank by 24H returns:

```bash
poetry run python3 MomentumScanner.py DEX
```
2. Scan intraday returns for a DEX and rank by integer hours:
```bash
poetry run python3 MomentumScanner_intraday.py DEX Hours
```
Hours is an integer between 1 and 23.

3. Calculate technical indicator (currently available INDICATOR_NAME: MACD_ratio (MACD ratio), RSI, BB_updiff (BollingerBand upthrend ratio)) for a DEX:
```bash
poetry run python3 MomentumScanner_techindicator.py DEX INDICATOR_NAME
```

4. Scan high momentum tokens on a DEX and store the data in a SQLite database:
```bash
python run_momentum_table.py DEX Hours Daily_Volume Monthly_Aeverage_Volune Liquidity
```

5. Calculate stop-loss and profit-taking price for a token.
```bash
$ python run_risk_query.py TOKEN StopLoss ProfitTaking
```
`TOKEN` = token name, `StopLoss` = stop-loss percentage, `ProfitTaking` = profit-taking percentage.
If `StopLoss` and `ProfitTaking` not included, the default values 5% will be used for both. For example:
```bash
$ python run_risk_query.py bitcoin
```

The script currently supports the all DEXes on CoinGecko. Check all ids in
https://api.coingecko.com/api/v3/exchanges
