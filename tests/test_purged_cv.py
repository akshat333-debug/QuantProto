"""Tests for purged & embargoed K-fold cross-validation."""

import numpy as np
import pytest

from quantproto.integrity.purged_cv import PurgedKFold


class TestPurgedKFold:
    def test_validates_params(self):
        with pytest.raises(ValueError):
            PurgedKFold(n_splits=1)
        with pytest.raises(ValueError):
            PurgedKFold(purge=-1)
        with pytest.raises(ValueError):
            PurgedKFold(embargo_pct=1.5)

    def test_yields_n_splits(self):
        cv = PurgedKFold(n_splits=5, purge=2, embargo_pct=0.02)
        folds = list(cv.split(500))
        assert len(folds) == 5

    def test_no_train_test_overlap(self):
        cv = PurgedKFold(n_splits=5, purge=3, embargo_pct=0.02)
        for train, test in cv.split(500):
            assert len(np.intersect1d(train, test)) == 0

    def test_purge_gap_respected(self):
        purge = 3
        cv = PurgedKFold(n_splits=5, purge=purge, embargo_pct=0.0)
        for train, test in cv.split(500):
            t0, t1 = test[0], test[-1]
            # No training index within `purge` of the test block edges.
            for idx in train:
                assert not (t0 - purge <= idx <= t1 + purge) or idx < t0 - purge or idx > t1 + purge

    def test_embargo_after_test(self):
        cv = PurgedKFold(n_splits=5, purge=0, embargo_pct=0.05)
        n = 1000
        embargo = int(n * 0.05)
        for train, test in cv.split(n):
            t1 = test[-1]
            forbidden = set(range(t1 + 1, t1 + 1 + embargo))
            assert forbidden.isdisjoint(set(train.tolist()))

    def test_all_test_indices_cover_series(self):
        cv = PurgedKFold(n_splits=4, purge=1, embargo_pct=0.0)
        covered = np.concatenate([test for _, test in cv.split(200)])
        assert np.array_equal(np.sort(covered), np.arange(200))
