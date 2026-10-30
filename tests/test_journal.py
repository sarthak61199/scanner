import pandas as pd
import pytest


@pytest.mark.parametrize('rule',['fixed','breakeven','ema_trail','chandelier'])
def test_lifecycle(database,prices,rule,monkeypatch):
    import journal as j
    import backtest as b
    monkeypatch.setattr(j,'MAX_OPEN',1)
    d=prices(1)
    plans=pd.DataFrame([dict(symbol=s,setup='signal',sector='IT',entry=100.,stop=90.,qty=100,score=score)
                        for s,score in [('A',3),('B',2),('C',1)]])
    rules=[dict(key='signal',setup='signal',filters=[],exit=rule,stop_atr=2.,test={'taken_avg_r':.2})]
    frames={s:d for s in ['A','B','C']}
    rejected=[('B','signal','debt')]
    j.open_trades(1,plans,plans.iloc[[0,2]],rejected,frames,rules)
    j.open_trades(1,plans,plans.iloc[[0,2]],rejected,frames,rules)
    rows=database.rows('SELECT * FROM paper_trades ORDER BY score DESC')
    assert len(rows)==3
    assert [r['taken'] for r in rows]==[1,0,0]
    assert rows[1]['rejected']=='debt'
    assert rows[0]['backtest_slot_r']==.2
    d=prices(2)
    j.update_trades({s:d for s in frames})
    assert all(r['days']==1 for r in database.rows('SELECT * FROM paper_trades'))
    d=prices(3,Open=[100,100,85],Low=[99,99,80])
    j.update_trades({s:d for s in frames})
    expected=b.simulate_trade(d,0,exit_rule=rule)
    for r in database.rows('SELECT * FROM paper_trades'):
        assert r['status']=='closed'
        for key in ['exit','reason','days','R','gross_R']:
            assert r[key]==expected[key]
    before=database.rows('SELECT * FROM paper_trades')
    j.update_trades({s:d for s in frames})
    assert database.rows('SELECT * FROM paper_trades')==before
    stats=j.journal_stats()
    assert stats['overall']['taken']['closed']==1
    assert stats['overall']['rejected']['closed']==1
    assert stats['overall']['accepted']['closed']==2


def test_empty_statistics(database):
    import journal as j
    stats=j.journal_stats()
    assert stats['overall']['taken']['avg_r'] is None
    assert stats['go_live']['ready'] is False
    assert j._range(pd.Series([1.]))==(None,None)
    assert j._range(pd.Series([1.,1.]))==(1.,1.)


def test_group_excludes_open_returns(database):
    import journal as j
    t=pd.DataFrame({'status':['open','closed','closed'],'R':[100.,1.,-1.]})
    g=j._group(t)
    assert (g['n'],g['open'],g['closed'],g['avg_r'],g['win'],g['total_r'])==(3,1,2,0.,.5,0.)


@pytest.mark.parametrize('lag,expected',[(9,1),(10,2)])
def test_cooldown(database,prices,lag,expected):
    import journal as j
    p=pd.DataFrame([dict(symbol='A',setup='signal',sector='IT',entry=100.,stop=90.,qty=100,score=1.)])
    v=[dict(key='signal',setup='signal',filters=[],exit='fixed',stop_atr=2.,test={'taken_avg_r':.2})]
    j.open_trades(1,p,p,[],{'A':prices(1)},v)
    with database.connect() as c:
        c.execute("UPDATE paper_trades SET status='closed'")
    j.open_trades(2,p,p,[],{'A':prices(lag+1)},v)
    assert len(database.rows('SELECT * FROM paper_trades'))==expected


def test_missing_prices_leave_trade_unchanged(database,prices,monkeypatch):
    import journal as j
    import data
    p=pd.DataFrame([dict(symbol='A',setup='signal',sector='IT',entry=100.,stop=90.,qty=100,score=1.)])
    v=[dict(key='signal',setup='signal',filters=[],exit='fixed',stop_atr=2.,test={'taken_avg_r':.2})]
    j.open_trades(1,p,p,[],{'A':prices(1)},v)
    before=database.rows('SELECT * FROM paper_trades')
    monkeypatch.setattr(data,'download',lambda symbols: {})
    j.update_trades({})
    assert database.rows('SELECT * FROM paper_trades')==before
