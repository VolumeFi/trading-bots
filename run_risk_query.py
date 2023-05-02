from momentum_scanner_intraday import get_risk_query
from sys import argv

def main():
    if len(argv) == 1:
        print('No input')
        return
    elif len(argv) == 2:
        token = str(argv[1])
        slprice, ptprice = get_risk_query(token, stoploss=0.05, profittaking=0.05)
        print('default stop-loss 5% and profit-taking 5%:')
    elif len(argv) == 4:
        token = str(argv[1])
        sl = float(argv[2])
        pt = float(argv[3])
        slprice, ptprice = get_risk_query(token, stoploss=sl, profittaking=pt)
    else:
        print('Wrong input format')
        return
        
if __name__ == '__main__':
    main()