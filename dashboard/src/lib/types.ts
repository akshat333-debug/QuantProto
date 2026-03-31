/* ─── Shared Types ─────────────────────────────────────────────── */

export type GateViolation = { metric: string; value: number; rule: string; limit: number };
export type BootstrapCI = { lower: number; upper: number; point: number };

export type AnalysisData = {
    summary: {
        action: string; sharpe: number; sortino: number; var_95: number;
        cvar_95: number; max_drawdown: number; calmar: number; pain_index: number;
        total_return: number; n_splits: number; gate_passed: boolean;
        gate_violations: GateViolation[];
        bootstrap_ci: BootstrapCI;
    };
    equity_curve: { dates: string[]; values: number[] };
    drawdown: { dates: string[]; values: number[] };
    regime: { dates: string[]; states: string[]; confidence: number[] };
    portfolio: { tickers: string[]; mean_variance: number[]; risk_parity: number[]; max_sharpe: number[] };
    correlation: { tickers: string[]; matrix: number[][] };
    pca: { explained_variance: number[]; components: string[] };
    assets: { ticker: string; annualised_return: number; annualised_vol: number; sharpe: number; max_drawdown: number; latest_price: number }[];
    rolling_correlation: { dates: string[]; values: number[] };
};

export type StressData = {
    scenario: { name: string; max_drawdown: number; total_return: number; worst_day: number; var_95: number; equity: number[] };
    monte_carlo: { median_terminal: number; p5: number; p95: number; prob_loss: number; worst_dd: number; paths: number[][] };
};

export type TooltipPayload = { color: string; name: string; value: number | string };
