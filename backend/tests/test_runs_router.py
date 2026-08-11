from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.db import Base
from app.routers.runs import list_runs


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/runs_router_test.db")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed(db, run_count: int):
    site = models.Site(name="Paginated Site", base_url="https://example.com")
    account = models.Account(site=site, label="demo", username="u", encrypted_password=b"x")
    db.add_all([site, account])
    db.flush()

    base = datetime(2026, 1, 1, 9, 0, 0)
    for i in range(run_count):
        db.add(
            models.CheckRun(
                site_id=site.id,
                account_id=account.id,
                status=models.RunStatus.success,
                started_at=base + timedelta(minutes=i),
                finished_at=base + timedelta(minutes=i, seconds=5),
                duration_ms=5000,
            )
        )
    db.commit()
    return site


def test_total_reflects_every_run_even_when_limit_truncates_the_page(db_session):
    site = _seed(db_session, run_count=168)
    page = list_runs(site.id, limit=50, offset=0, db=db_session)
    assert page.total == 168
    assert len(page.items) == 50


def test_pages_are_ordered_newest_first_with_no_overlap_or_gap(db_session):
    site = _seed(db_session, run_count=120)
    page1 = list_runs(site.id, limit=50, offset=0, db=db_session)
    page2 = list_runs(site.id, limit=50, offset=50, db=db_session)
    page3 = list_runs(site.id, limit=50, offset=100, db=db_session)

    assert [r.started_at for r in page1.items] == sorted((r.started_at for r in page1.items), reverse=True)
    assert page1.items[-1].started_at > page2.items[0].started_at  # no gap/overlap at the boundary
    assert page2.items[-1].started_at > page3.items[0].started_at
    assert len(page3.items) == 20  # 120 total - 100 offset


def test_offset_past_the_end_returns_no_items_but_correct_total(db_session):
    site = _seed(db_session, run_count=10)
    page = list_runs(site.id, limit=50, offset=100, db=db_session)
    assert page.items == []
    assert page.total == 10
