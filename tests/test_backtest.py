import pandas as pd
import pytest
import backtest as b


@pytest.mark.parametrize('entry,risk,expected', [(100,10,100),(100,1,200),(30000,100,0),(0,1,0),(100,0,0)])
def test_sizing(entry, risk, expected):
    assert b.position_size(entry, risk) == expected


@pytest.mark.parametrize('o,h,l,reason,exit_px', [(85,105,80,'stop_gap',85),(125,130,95,'target_gap',125),
    (100,125,85,'stop',90),(100,125,95,'target',120)])
def test_fills(prices,o,h,l,reason,exit_px):
    d=prices(2, Open=[100,o],High=[150,h],Low=[50,l])
    t=b.simulate_trade(d,0)
    assert (t['reason'],t['exit'],t['days']) == (reason,exit_px,1)
    assert t['gross_R'] == round((exit_px-100)*100/1000,3)
    assert t['R'] == round((exit_px-100)*100/1000-.025,3)
    assert t['exit_date'] == d.index[1]


@pytest.mark.parametrize('rule,days', [('fixed',30),('breakeven',30),('ema_trail',60),('chandelier',60)])
def test_timeout_and_partial(prices,rule,days):
    assert b.simulate_trade(prices(1),0,exit_rule=rule) is None
    assert b.simulate_trade(prices(1),0,exit_rule=rule,partial=True)['days']==0
    assert b.simulate_trade(prices(days),0,exit_rule=rule,partial=True)['status']=='open'
    t=b.simulate_trade(prices(days+1),0,exit_rule=rule)
    assert (t['reason'],t['days'])==('time',days)


@pytest.mark.parametrize('rule', ['fixed+mkt','chandelier+mkt'])
def test_market_exit(prices,rule):
    assert b.simulate_trade(prices(2,mkt_weak=[False,True]),0,exit_rule=rule)['reason']=='market'


def test_trailing_rules(prices):
    d=prices(3,High=[101,111,101],Low=[99,95,99])
    assert b.simulate_trade(d,0,exit_rule='breakeven')['exit']==100
    state=b.simulate_trade(d.iloc[:2],0,exit_rule='breakeven',partial=True)
    assert state['stop']==100
    assert b.simulate_trade(prices(2,Close=[100,94]),0,exit_rule='ema_trail')['reason']=='trail'
    d=prices(3,High=[101,110,105],atr=[5,2,5],Low=[99,99,103],Open=[100,100,105])
    assert b.simulate_trade(d,0,exit_rule='chandelier')['exit']==104


def test_backtest_selection(prices):
    d=prices(24,signal=True)
    _,tr=b.backtest({'A':d},'signal')
    assert [t['date'] for t in tr]==list(d.index[[0,10,20]])
    assert all(t['reason']=='open' for t in tr)
    assert b.backtest({'A':prices(3,signal=True,turnover_cr=0)},'signal')[1]==[]


def test_summary_and_capacity():
    t=pd.DataFrame({'date':pd.to_datetime(['2026-01-01','2026-01-01','2026-01-02']),
        'exit_date':pd.to_datetime(['2026-01-02']*3),'score':[1,2,1],'R':[-1,2,-2]})
    assert list(b.capped_trades(t,1).index)==[1,2]
    assert b.risk_stats(t)==(2.,1)
    assert b.risk_stats(pd.DataFrame())==(None,None)
