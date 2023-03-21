import requests
import pandas as pd
import time

def querydex(dex):
    url = 'https://api.coingecko.com/api/v3/exchanges/' + dex
    try:
        re = requests.get(url, timeout=10)
        return re
    except:
        print('timed out')
        return None

def querytokenprice1d(token):
    url = 'https://api.coingecko.com/api/v3/coins/'+token+'/market_chart?vs_currency=usd&days=1'
    try:
        re = requests.get(url, timeout=10)
        return re
    except:
        print('timed out')
        return None

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

def tokenprice(token):
    query = querytokenprice1d(token)
    try:
        prices = query.json()['prices']
    except:
        return 0
    
    price = prices[-1][1]
    return price

def queryvolumes(dex):
    query = querydex(dex)
    try:
        dexdata = query.json()['tickers']
    except:
        return pd.DataFrame()
    
    vols = pd.Series(dtype=float)
    for i in dexdata:
        id_ = i['coin_id'] + '<>' + i['target_coin_id']
        vols.loc[id_] = i['converted_volume']['usd']
        
    return vols.sort_values(ascending=False)

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

def getrisk(price, stoploss, profittaking):
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    return slprice, ptprice

def gettrades(token, stoploss, profittaking):
    price = tokenprice(token)
    sl, pt = getrisk(price, stoploss, profittaking)
    return price, sl, pt

def findbestreturn(dex, stoploss, profittaking):
    vols = queryvolumes(dex)
    if len(vols) != 0:
        vols1=filerpairs(vols, volume=1e5)
        if len(vols1) == 0:
            print('No pair found with enough volume')
            return
        else:
            vols1 = vols1.iloc[:5]
    else:
        print('Endpoint issues, query did not get any returned values')
        return 
        
    rets24h = findrets24h(vols1)
    rets24h = rets24h.sort_values(by='24H Return',ascending=False)
    rets24h['24H Return'] = rets24h['24H Return'].apply(lambda x: str(round(x*100,2))+'%')
    hottoken = rets24h.index[0]
    time.sleep(1)
    enterprice, sl, pt = gettrades(str(hottoken), stoploss, profittaking)
    
    print(dex,' top winners: ', flush=True)
    print(rets24h, flush=True)
    print('* * * * *', flush=True)
    print('Hottest token in the past 24H: ', flush=True)
    print(hottoken, ', 24H return: ', rets24h['24H Return'].iloc[0], flush=True)
    if enterprice != 0:
        print('Enter at: ', enterprice,flush=True)
        print('Stop-loss at: ', sl, ' (stop loss percentage: ', stoploss,')', flush=True)
        print('Profit-taking at: ', pt,' (profit taking percentage: ', profittaking,')', flush=True)
    else:
        print('Enter price, stop-loss and profit-taking calculation failed due to endpoint issue', flush=True)
    print('----------------------------------------------', flush=True)

if __name__ == '__main__':
    #findbestreturn(dex='apeswap_bsc')
    findbestreturn(dex='pancakeswap_new', stoploss=0.05, profittaking=0.05)
