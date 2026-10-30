import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def database(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, 'DB_PATH', str(tmp_path / 'test.db'))
    import db
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'test.db'))
    db.init_db()
    import journal
    monkeypatch.setattr(journal, 'latest_validated', lambda: None)
    monkeypatch.setattr(journal, '_now', lambda: '2026-10-30 17:00:00')
    return db


@pytest.fixture
def prices():
    def make(n=3, **columns):
        d = pd.DataFrame(dict(Open=100., High=101., Low=99., Close=100., atr=5.,
                              ema20=95., mkt_weak=False, signal=False,
                              turnover_cr=10., ret63=.1, score=.5),
                         index=pd.bdate_range('2026-01-01', periods=n))
        for key, value in columns.items():
            d[key] = value
        return d
    return make
