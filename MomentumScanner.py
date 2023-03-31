import requests
import pandas as pd
import time, sys, os
import argparse

#apiroot = 'https://api.coingecko.com/api/v3'
#apikey = ''
apiroot = 'https://pro-api.coingecko.com/api/v3'
apikey = 'x_cg_pro_api_key=' + os.environ['CG_KEY']

def querydex(dex):
    url = apiroot + '/exchanges/' + dex + '?' + apikey
    try:
        re = requests.get(url, timeout=10)
        return re
    except:
        print('timed out')
        return None

def querytokenprice1d(token):
    url = apiroot + '/coins/'+token+'/market_chart?vs_currency=usd&days=1' + '&' + apikey
    try:
        re = requests.get(url, timeout=10)
        return re
    except:
        print('timed out')
        return None
    
def querycoin(coin):
    url = 'https://pro-api.coingecko.com/api/v3/coins/'+coin+'?'+apikey
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

def filterpairs(vols, volume=1e5):
    vols = vols[vols >= volume]
    return vols

def findtoken(pair):
    a = pair.split('<>')
    if a[0] in ['wbnb','binance-usd','weth']:
        return a[1]
    else:
        return a[0]

def querytokens_price1d(tokens):
    token_ids = ''
    for i,token in enumerate(tokens):
        if i == len(tokens) - 1:
            token_ids += token
        else:
            token_ids += token + '%2C'
    url = apiroot + '/simple/price?ids='+token_ids+'&vs_currencies=usd&include_24hr_change=true' + '&' + apikey
    #print(url)
    try:
        re = requests.get(url, timeout=10)
        return re
    except:
        print('timed out')
        return None

def tokens_ret24h(tokens):
    query = querytokens_price1d(tokens)
    ret24 = pd.DataFrame()
    try:
        q = query.json()
        for k in q.keys():
            ret24.loc[k,'24H Return'] = q[k]['usd_24h_change']
    except Exception as e:
        print('error:',e)
        pass
    return ret24

def add_7drets(df):
    df['7D Return'] = None
    for i in df.index:
        try:
            re = querycoin(i)
            ret7d = re.json()['market_data']['price_change_percentage_7d']
            df.loc[i,'7D Return'] = ret7d
        except:
            df.loc[i,'7D Return'] = None
    return df

def findrets24h(vols):
    tokens = []
    rets24h = pd.DataFrame()
    for pair in vols.index:
        if 'wbnb' in pair or 'binance-usd' in pair or 'weth' in pair:
            token = findtoken(pair)
            if token not in tokens:
                tokens.append(token)
    rets24h = tokens_ret24h(tokens)
    rets24h.index.name = 'Token name'
    return rets24h

def getrisk(price, stoploss, profittaking):
    slprice = price * (1 - stoploss)
    ptprice = price * (1 + profittaking)
    return slprice, ptprice

def getriskquery(token, stoploss=0.05, profittaking=0.05):
    re = querytokens_price1d([token])
    try:
        price = re.json()[token]['usd']
        slprice = price * (1 - stoploss)
        ptprice = price * (1 + profittaking)
        print('enter at:',price, 'stop-loss:',slprice,'profit-taking:',ptprice)
        #return slprice, ptprice
    except:
        print('query failed, try again shortly')

def gettrades(token, stoploss, profittaking):
    price = tokenprice(token)
    sl, pt = getrisk(price, stoploss, profittaking)
    return price, sl, pt

def findliquidity(coin, dex):
    re = querycoin(coin)
    for ticker in re.json()['tickers']:
        if ticker['market']['identifier'] == dex:
            #print('DEX: ',ticker['market']['identifier'],ticker['volume'])
            print('DEX: ',ticker['market']['identifier'],
                  ', Pair: ',ticker['target_coin_id'],'<>',ticker['coin_id'],', Volume: ',ticker['volume'])

def findbestreturn(dex, stoploss, profittaking, neg7D):
    vols = queryvolumes(dex)
    if len(vols) != 0:
        vols1=filterpairs(vols, volume=1e5)
        if len(vols1) == 0:
            print('No pair found with enough volume')
            return
        else:
            vols1 = vols1#.iloc[1:]
    else:
        print('Endpoint issues, query did not get any returned values')
        return 
        
    rets24h = findrets24h(vols1)
    rets24h = rets24h.sort_values(by='24H Return',ascending=False)
    rets24h = rets24h[rets24h['24H Return']>=0]
    rets24h = add_7drets(rets24h)
#    rets24h['24H Return'] = rets24h['24H Return'].apply(lambda x: str(round(x*100,2))+'%')
    rets24h['24H Return'] = rets24h['24H Return'].apply(lambda x: str(round(x,2))+'%')
    if neg7D:
        rets24h = rets24h[rets24h['7D Return']<0]
        if len(rets24h) == 0:
            print('No hot tokens with negative 7D return')
            return

    try:
        rets24h['7D Return'] = rets24h['7D Return'].apply(lambda x: str(round(x,2))+'%')
    except:
        pass

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
    print('* * * * *', flush=True)
    print('liquidity profile: ', flush=True)
    findliquidity(hottoken, dex)
    print('----------------------------------------------', flush=True)

if __name__ == '__main__':
    #findbestreturn(dex='apeswap_bsc', stoploss=0.05, profittaking=0.05)
    args = sys.argv

    if 'neg7D' in args:
        neg7D = True
        args.remove('neg7D')
    else:
        neg7D = False

    if len(args) == 1:
        findbestreturn(dex='pancakeswap_new', stoploss=0.05, profittaking=0.05,neg7D=neg7D)
    elif len(args) == 2:
        findbestreturn(dex=str(sys.argv[1]), stoploss=0.05, profittaking=0.05,neg7D=neg7D)
