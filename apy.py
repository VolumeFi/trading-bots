import datetime
import pandas as pd

def pnl_per_trade(entry_usd, exit_usd):
    """
    pnl denom in usd for each trade
    """
    pnl_usd = exit_usd - entry_usd
    return pnl_usd

def return_per_trade(entry_usd, exit_usd):
    """
    return for each trade
    """
    pnl_usd = pnl_per_trade(entry_usd, exit_usd)
    ret = pnl_usd / entry_usd
    return ret

def get_trades_per_user(user_id):
    """
    TODO:
    """
    trades = {'id1':{'entry_timestamp':None,
                         'entry_usd':None,
                         'exit_timestamp':None,
                         'exit_usd':None}}
    return trades

def get_returns(trades: dict):
    rets = pd.Seris()
    for trade_id in trades:
        entry_time = pd.to_datetime(trades[trade_id]['entry_timestamp'])
        entry_usd = trades[trade_id]['entry_usd']
        exit_usd = trades[trade_id]['exit_usd']
        ret = return_per_trade(entry_usd, exit_usd)
        rets.loc[entry_time] = ret
        
    return rets

def get_duration(start, end):
    dur = end - start
    dur_days = dur.days + dur.seconds / 3600 / 24
    return dur_days

def get_apy(user_id):
    """
    TODO
    """
    trades = get_trades_per_user(user_id)
    rets = get_returns(trades)
    cumret = rets.sum()
    duration = get_duration(rets.index[0], rets.index[-1])
    cumret_annual = cumret * 365 / duration
    return cumret, cumret_annual
