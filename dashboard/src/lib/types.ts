/* ─── Shared Types ─────────────────────────────────────────────── */

export type GateViolation = { metric: string; value: number; rule: string; limit: number };
export type BootstrapCI = { lower: number; upper: number; point: number };

export type RobustnessVerdict = "robust" | "fragile" | "likely_overfit";

export type RedFlag = { severity: "high" | "medium" | "low"; code: string; message: string };
export type ChecklistItem = { code: string; question: string; why: string };

export type IntegrityReport = {
    score: number;
    verdict: RobustnessVerdict;
    headline: string;
    components: {
        significance: number; selection: number; cost_survival: number;
        sample_adequacy: number; red_flag_penalty: number;
        max: { significance: number; selection: number; cost_survival: number; sample_adequacy: number };
    };
    statistics: {
        sharpe_annualized: number; psr: number; dsr: number | null;
        skew: number; kurtosis: number; n_obs: number; n_trials: number;
        min_track_record_length: number | null; breakeven_bps: number | null;
    };
    pbo: { pbo: number; oos_degradation: number; prob_oos_loss: number; n_configs: number; logits: number[] } | null;
    cost_curve: { bps_grid: number[]; net_sharpe: number[] };
    red_flags: RedFlag[];
    checklist: ChecklistItem[];
    notes: string[];
    run_id?: string | null;
};

export type AnalysisData = {
    run_id?: string | null;
    data_source_used?: string;
    integrity?: IntegrityReport | null;
    summary: {
        action: string; sharpe: number; sortino: number; var_95: number;
        cvar_95: number; max_drawdown: number; calmar: number; pain_index: number;
        total_return: number; n_splits: number; gate_passed: boolean;
        gate_violations: GateViolation[];
        bootstrap_ci: BootstrapCI;
        robustness_score?: number | null;
        robustness_verdict?: RobustnessVerdict | null;
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
