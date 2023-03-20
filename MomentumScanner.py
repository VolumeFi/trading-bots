import requests
import pandas as pd
import time

def querydex(dex):
    url = 'https://api.coingecko.com/api/v3/exchanges/' + dex
    re = requests.get(url)
    return re

def querytokenprice1d(token):
    url = 'https://api.coingecko.com/api/v3/coins/'+token+'/market_chart?vs_currency=usd&days=1'
    re = requests.get(url)
    return re

def tokenreturn24h(token):
    query = querytokenprice1d(token)
    try:
        prices = query.json()['prices']
    except:
        return 0
    
    closeprice = prices[-1][1]
    openprice = prices[0][1]
    
    if openprice == 0:
        return 0
    else:
        ret24h = (closeprice - openprice) / openprice
        return ret24h

def queryvolumes(dex, n_pairs=10):
    query = querydex(dex)
    try:
        dexdata = query.json()['tickers']
    except:
        return pd.DataFrame()
    
    vols = pd.Series(dtype=float)
    for i in dexdata:
        id_ = i['coin_id'] + '<>' + i['target_coin_id']
        vols.loc[id_] = i['converted_volume']['usd']
        
    return vols.sort_values(ascending=False).head(n_pairs)

def filerpairs(vols, volume=1e5):
    vols = vols[vols >= volume]
    return vols

def findtoken(pair):
    a = pair.split('<>')
    if a[0] in ['wbnb','binance-usd']:
        return a[1]
    else:
        return a[0]
    
def findrets24h(vols):
    scanned = []
    rets24h = pd.DataFrame()
    for pair in vols.index:
        if 'wbnb' in pair or 'binance-usd' in pair:
            token = findtoken(pair)
            if token not in scanned:
                ret24h = round(tokenreturn24h(token),3)
                scanned.append(token)
                rets24h.loc[token,'24H Return'] = ret24h

                time.sleep(0.1)
    rets24h.index.name = 'Token name'
    return rets24h

def findbestreturn(dex='apeswap_bsc'):
    vols = queryvolumes(dex, n_pairs=10)
    if len(vols) != 0:
        vols1=filerpairs(vols, volume=1e3)
    else:
        print('no query')
        return 
        
    rets24h = findrets24h(vols1)
    rets24h = rets24h.sort_values(by='24H Return',ascending=False)
    rets24h['24H Return'] = rets24h['24H Return'].apply(lambda x: str(round(x*100,2))+'%')
    
    print(dex,' top winners: ')
    print(rets24h)
    print('* * * * *')
    print('Hottest token in the past 24H: ')
    print(rets24h.index[0], ', 24H return: ', rets24h['24H Return'].iloc[0])
    print('----------------------------------------------')

if __name__ == '__main__':
    findbestreturn(dex='apeswap_bsc')
    findbestreturn(dex='pancakeswap_new')
