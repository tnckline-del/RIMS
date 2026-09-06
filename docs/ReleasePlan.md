# RIMS Release Plan

The RIMS development process is organized into sequential numbered sprints.

Each sprint is a controlled development increment with defined scope,
implementation, testing, documentation, and Git completion.

The sprint history is maintained in `CHANGELOG.md`.

---

# Current Release

## Version 0.2.x

**Status:** In Development

The 0.2.x release establishes the core RIMS architecture and portfolio
data foundation.

### Completed Sprints

- Sprint 1 — Project Definition
- Sprint 2 — Project Architecture
- Sprint 3 — Change Management
- Sprint 4 — Repository Configuration
- Sprint 5 — Runtime Dependencies
- Sprint 6 — Build Entry Point
- Sprint 7 — Application Package
- Sprint 8 — Holding Entity
- Sprint 9 — Portfolio Entity
- Sprint 10 — Schwab CSV Import and Reconciliation
- Sprint 11 — Authoritative Schwab Market Values

---

# Next Development

## Sprint 12 — Historical Portfolio Snapshot

**Status:** Planned

### Objective

Establish the RIMS historical snapshot capability so that portfolio
information can be preserved at specific points in time without
overwriting prior data.

### Planned capabilities

- Point-in-time portfolio snapshots.
- Snapshot dates.
- Historical holdings.
- Historical shares.
- Historical market values.
- Historical cost basis.
- Historical forward annual dividend income.
- Historical portfolio yield.
- Historical cash.
- Preservation of historical information.
- Comparison of current and historical portfolio states.

### Acceptance criteria

Sprint 12 will be considered complete when:

- A portfolio can be captured as a dated snapshot.
- Snapshot data is independent of the current portfolio.
- Historical snapshots are not overwritten.
- Market values use authoritative source values when available.
- Forward annual dividend income is preserved.
- Historical portfolio metrics can be retrieved.
- Business logic is tested.
- Documentation is complete.
- Changes are committed and pushed to Git.

---

# Future Development

The following capabilities remain in the RIMS backlog and will be
assigned sequential sprint numbers as development proceeds.

## Portfolio Analysis

- Portfolio Health Score
- Position concentration analysis
- Income concentration analysis
- Dividend safety analysis
- Portfolio income trend analysis

## Investment Management

- Research & Opportunities
- Investment Thesis Library
- Replacement Analyzer
- Watch List management
- Dividend Calendar

## Advisor Management

- Advisor Scorecard
- Advisor recommendation tracking
- Advisor activity analysis

## Retirement Planning

- Retirement Forecasting
- Income Stress Testing
- RMD planning
- Tax planning
- Roth Conversion Planning

## Data Integration

- Stock Rover integration
- Additional portfolio data sources
- Historical market and dividend data

## Advanced Decision Support

- AI Portfolio Review
- Advanced retirement-income decision support

---

# Release Philosophy

RIMS development will prioritize a stable core architecture before
adding advanced analytical or presentation features.

Backlog capabilities will not be implemented merely because they are
available.

Each capability must support the primary RIMS mission:

> Generate dependable retirement income while preserving capital over
> the long term.

---

# Sprint Management Rules

1. Sprint numbers are sequential and permanent.
2. A completed sprint number will not be reused.
3. Each sprint must have defined scope and acceptance criteria.
4. Each sprint must be tested before completion.
5. Completed work must be documented in `CHANGELOG.md`.
6. Completed code must be committed to Git.
7. Completed code must be pushed to GitHub.
8. The repository must be left with a clean working tree.
9. New functionality should not be added until its required
   architectural foundation is stable.
10. Backlog priorities may be adjusted when justified by the needs of
    the retirement-income management system.

---

# Version Roadmap

## Version 0.2.x

Core application foundation.

Focus:

- Project architecture
- Core data model
- Schwab import
- Portfolio reconciliation
- Authoritative source data
- Historical snapshots

---

## Version 1.x

Retirement Income Management System.

Target capabilities:

- Complete portfolio management
- Historical portfolio analysis
- Income monitoring
- Dividend monitoring
- Watch List
- Investment research
- Advisor management
- Retirement-income reporting
- Initial retirement planning capabilities

---

## Version 2.x

Advanced Portfolio Analytics.

Target capabilities:

- Advanced portfolio analytics
- Income stress testing
- Portfolio health scoring
- Advisor performance analysis
- Advanced investment decision support
- Expanded historical analysis

---

## Version 3.x

Retirement Income Decision Support System.

Target capabilities:

- Integrated retirement-income planning
- Advanced forecasting
- Tax and RMD analysis
- Comprehensive scenario analysis
- Advanced decision support

---

# Guiding Development Principle

Build the foundation first.

Add analytical capability only when the underlying data is reliable.

Add presentation capability only when the underlying analysis is reliable.

Add automation only when the underlying process is reliable.

RIMS should favor correctness, transparency, maintainability, and
long-term usefulness over rapid feature expansion.