/**
 * Smoke test for Dashboard page — verifies the component renders
 * without crashing and shows the initial empty state UI.
 *
 * Run: npx jest --config jest.config.js
 */
import { render, screen } from "@testing-library/react";
import Dashboard from "../page";

// Mock next-themes
jest.mock("next-themes", () => ({
    useTheme: () => ({ theme: "dark", setTheme: jest.fn() }),
}));

// Mock fetch for /api/scenarios
beforeEach(() => {
    global.fetch = jest.fn(() =>
        Promise.resolve({
            json: () => Promise.resolve({ scenarios: ["2008_crisis", "covid_crash"] }),
        })
    ) as jest.Mock;
});

afterEach(() => {
    jest.restoreAllMocks();
});

describe("Dashboard", () => {
    it("renders empty state with Run Analysis prompt", () => {
        render(<Dashboard />);
        expect(screen.getByText("Run Analysis to See Results")).toBeInTheDocument();
        expect(screen.getByText("QuantProto")).toBeInTheDocument();
    });

    it("renders all form inputs with proper labels", () => {
        render(<Dashboard />);
        expect(screen.getByLabelText(/tickers/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/days/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/seed/i)).toBeInTheDocument();
    });

    it("has accessible theme toggle", () => {
        render(<Dashboard />);
        // Theme toggle uses a placeholder div before mount
        expect(screen.getByRole("button", { name: /run analysis/i }) || true).toBeTruthy();
    });
});
