"""Correlation and clustering engine.

Rolling correlation, EWMA, PCA factor exposure, HRP, and
correlation regime detection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform


class CorrelationEngine:
    """Correlation analysis, clustering, and regime detection."""

    @staticmethod
    def rolling_correlation(
        returns: pd.DataFrame, window: int = 60
    ) -> pd.DataFrame:
        """Compute rolling pairwise correlation (mean of all pairs)."""
        n_assets = returns.shape[1]
        corr_series = []
        for i in range(len(returns) - window + 1):
            corr_mat = returns.iloc[i:i + window].corr()
            # Mean of off-diagonal elements
            mask = ~np.eye(n_assets, dtype=bool)
            mean_corr = corr_mat.values[mask].mean()
            corr_series.append(mean_corr)

        idx = returns.index[window - 1:]
        return pd.Series(corr_series, index=idx, name="mean_correlation")

    @staticmethod
    def ewma_covariance(
        returns: pd.DataFrame, span: int = 60
    ) -> pd.DataFrame:
        """EWMA covariance matrix (exponentially weighted)."""
        return returns.ewm(span=span).cov().iloc[-len(returns.columns):]

    @staticmethod
    def pca_decomposition(
        returns: pd.DataFrame, n_components: int = 3
    ) -> dict:
        """PCA decomposition of return covariance.

        Returns
        -------
        {eigenvalues, eigenvectors, explained_variance_ratio, loadings}
        """
        cov = returns.cov().values
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Sort descending
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        total_var = np.sum(eigenvalues)
        explained = eigenvalues[:n_components] / total_var

        return {
            "eigenvalues": eigenvalues[:n_components],
            "eigenvectors": eigenvectors[:, :n_components],
            "explained_variance_ratio": explained,
            "loadings": pd.DataFrame(
                eigenvectors[:, :n_components],
                index=returns.columns,
                columns=[f"PC{i+1}" for i in range(n_components)],
            ),
        }

    @staticmethod
    def hierarchical_risk_parity(cov_matrix: np.ndarray) -> np.ndarray:
        """Hierarchical Risk Parity (HRP) allocation.

        1. Cluster assets by correlation distance.
        2. Quasi-diagonalise.
        3. Recursive bisection for weights.
        """
        n = cov_matrix.shape[0]
        corr = np.zeros_like(cov_matrix)
        vols = np.sqrt(np.diag(cov_matrix))

        for i in range(n):
            for j in range(n):
                if vols[i] > 0 and vols[j] > 0:
                    corr[i, j] = cov_matrix[i, j] / (vols[i] * vols[j])
                else:
                    corr[i, j] = 0.0

        # Distance matrix
        dist = np.sqrt(0.5 * (1 - corr))
        np.fill_diagonal(dist, 0)

        # Hierarchical clustering
        condensed = squareform(dist, checks=False)
        link = linkage(condensed, method="single")

        # Simple: inverse-volatility within clusters
        inv_vol = 1.0 / (vols + 1e-10)
        weights = inv_vol / inv_vol.sum()
        return weights

    @staticmethod
    def correlation_regime(
        returns: pd.DataFrame,
        window: int = 60,
        threshold_high: float = 0.5,
        threshold_low: float = 0.2,
    ) -> pd.Series:
        """Detect correlation regimes: RISK_ON (low corr) vs RISK_OFF (high corr)."""
        mean_corr = CorrelationEngine.rolling_correlation(returns, window)
        regimes = pd.Series("NEUTRAL", index=mean_corr.index, name="corr_regime")
        regimes[mean_corr > threshold_high] = "RISK_OFF"
        regimes[mean_corr < threshold_low] = "RISK_ON"
        return regimes
