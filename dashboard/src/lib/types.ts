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

/* ─── Experiment tracker ─────────────────────────────────────── */

export type ExperimentSummary = { name: string; created_ts: string; n_runs: number };

export type BudgetStatus = {
    n_runs: number;
    n_configs: number;
    budget_state: "empty" | "ok" | "warning" | "burned";
    message: string;
    best_run_id?: string;
    best_params?: Record<string, unknown>;
    best_sharpe_ann?: number;
    spurious_sharpe_ann?: number;
    haircut_sharpe_ann?: number;
    psr?: number;
    dsr?: number | null;
    pbo?: { pbo: number; oos_degradation: number; prob_oos_loss: number; n_configs: number } | null;
    n_obs_best?: number;
};

export type ExperimentRun = {
    id: string; seq: number; ts: string;
    params: Record<string, unknown>; params_hash: string;
    source: string; code_hash: string | null;
    n_obs: number; sharpe: number;
};

export type ExperimentDetail = {
    status: BudgetStatus;
    runs: ExperimentRun[];
    chain_valid: boolean;
};

export type SensitivityResult = {
    param: string;
    n_values: number;
    values: (number | string)[];
    sharpe_ann_by_value?: number[];
    peak_value?: number | string;
    neighbour_ratio?: number | null;
    verdict: "plateau" | "soft_peak" | "sharp_peak" | "inconclusive" | "insufficient";
    message: string;
};

export type DriftResult = {
    state: "no_backtest" | "no_live_data" | "insufficient_data" | "consistent" | "watch" | "diverging";
    message: string;
    n_live?: number;
    n_backtest?: number;
    backtest_sharpe_ann?: number;
    live_sharpe_ann?: number;
    consistency_prob?: number;
};
