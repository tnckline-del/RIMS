# Sprint 19P — RIMS Gap Assessment

**Status:** Complete

**Date:** 2026-09-16

---

## 1. Purpose

Sprint 19P is a formal look-back assessment of the RIMS project following completion of Sprint 19O.

The purpose is to:

- Review the original RIMS objectives.
- Assess the capabilities completed through Sprint 19O.
- Identify significant gaps between the current implementation and the intended product.
- Prevent unnecessary expansion of the analytical backend before the core application is complete.
- Establish the architectural direction for Sprint 20 and subsequent development.

Sprint 19P does not add production functionality.

---

## 2. Original Product Vision

RIMS was established as a professional software application intended to assist an income-focused retiree in managing investments.

The long-term product vision is for RIMS to become the primary management system for an income-oriented retirement portfolio.

The system is intended to integrate:

- Portfolio information.
- Historical records.
- Investment research.
- Advisor interactions.
- Objective portfolio analysis.

The primary objective is dependable retirement income while preserving capital over the long term.

RIMS is not intended to predict markets or function as a trading system.

---

## 3. Original Success Criteria

The original project definition established four questions that RIMS should answer within one minute of opening the Dashboard:

1. Is my retirement income becoming more secure?
2. Has projected annual income increased or decreased?
3. Which investments require attention?
4. What should be discussed with my financial advisor?

These questions remain the primary test of whether the eventual RIMS user interface is accomplishing its purpose.

---

## 4. Current Architectural Foundation

RIMS established the following system-of-record philosophy:

### Schwab

Schwab is authoritative for:

- Holdings.
- Market values.
- Cost basis.
- Transactions.

### RIMS

RIMS is authoritative for information and analysis not maintained by Schwab, including:

- Derived analysis.
- Goals.
- Notes.
- Watch status.
- Historical analysis.
- Forward-income assumptions.

Historical information must not be overwritten.

This separation remains appropriate and should be preserved as the application layer is developed.

---

## 5. Capability Assessment

### 5.1 Core Portfolio Model

**Status: COMPLETE**

RIMS has a functioning Portfolio and Holding model supporting:

- Shares.
- Price.
- Cost basis.
- Market value.
- Gain/loss.
- Forward annual dividend income.
- Portfolio yield.
- Income yield on cost.
- Position weight.
- Income contribution.
- Holding classification.

Forward annual dividend income has been established as the primary income metric.

### 5.2 Schwab Data Import

**Status: COMPLETE FOUNDATION**

RIMS can:

- Import Schwab CSV position data.
- Process multiple account sections.
- Identify securities.
- Identify cash and money-market positions.
- Process summary rows.
- Parse dates and numeric values.
- Consolidate duplicate securities.
- Reconcile market value.
- Reconcile cost basis.

Schwab market value is treated as authoritative while calculated market value remains available for validation.

The importer has been validated against actual Schwab portfolio data.

### 5.3 Historical Portfolio Snapshots

**Status: COMPLETE FOUNDATION**

RIMS can:

- Create point-in-time portfolio snapshots.
- Preserve historical holdings.
- Preserve historical market value.
- Preserve historical cost basis.
- Preserve historical income.
- Store snapshots persistently.
- Retrieve snapshots.
- List historical snapshot dates.

Historical snapshots are independent of the current portfolio.

### 5.4 Historical Portfolio Comparison

**Status: COMPLETE**

RIMS can compare historical portfolio states and identify:

- Market-value changes.
- Securities-value changes.
- Cash changes.
- Cost-basis changes.
- Gain/loss changes.
- Forward-income changes.
- Holding-count changes.
- Added holdings.
- Removed holdings.
- Common holdings.
- Holding-level changes.

Human-readable historical reports are also supported.

### 5.5 Historical Income Trend

**Status: COMPLETE FOUNDATION**

RIMS can analyze forward annual dividend income across historical snapshots.

It can identify:

- Beginning income.
- Ending income.
- Period-to-period income changes.
- Income percentage changes.
- Increasing trends.
- Decreasing trends.
- Stable trends.
- Largest income increases.
- Largest income decreases.

The system deliberately does not infer unsupported total-return or investment-performance conclusions.

### 5.6 Historical Transaction and Income Analysis

**Status: COMPLETE FOUNDATION**

RIMS now has persistent transaction storage and repository functionality.

The system has been validated against actual multi-account transaction data.

Historical income analysis can distinguish:

- Total income.
- Recurring income.
- Dividends.
- Interest.
- Capital-gain distributions.
- Special income.
- Reinvested income.
- Prior-year income.
- Income adjustments.

Historical income can also be reconciled against current portfolio holdings.

### 5.7 Current Income Position Analysis

**Status: COMPLETE**

RIMS can determine:

- Historical income associated with current holdings.
- Recurring historical income.
- Income contribution by current holding.
- Holdings with historical income.
- Holdings without historical income.
- Income concentration.
- Symbolless historical income.

The analysis deliberately avoids:

- Annualizing historical income.
- Projecting income.
- Substituting current yield for income.
- Double counting reinvested income.
- Treating zero-share holdings as current holdings.

### 5.8 Forward Income

**Status: COMPLETE FOUNDATION**

RIMS now supports explicit forward-income assumptions.

The system distinguishes between:

- Forward annual income per share.
- Forward annual income for a position.

Forward position income is:

    shares × expected annual income per share

The system does not silently convert historical income into forward income.

This distinction is important because RIMS is intended to manage the user's expected future retirement income rather than merely report historical distributions.

### 5.9 Forward Income Position Management

**Status: COMPLETE FOUNDATION**

RIMS can identify changes in forward-income assumptions and positions.

Supported change reasons include:

- New Position.
- Position Change.
- Dividend Change.
- Position & Dividend Change.
- No Change.
- Position Closed.

The lifecycle is:

    New
      ↓
    Active
      ↓
    Changed / No Change
      ↓
    Closed
      ↓
    Gone

The system maintains the current forward-income baseline required for change detection.

### 5.10 Forward Income Portfolio Report

**Status: COMPLETE**

RIMS can produce a portfolio-level forward-income report containing:

- Current holdings.
- Shares.
- Market value.
- Forward annual income.
- Percentage contribution to forward income.
- Change reason.
- Total market value.
- Total forward annual income.
- Holdings with forward-income assumptions.
- Holdings without forward-income assumptions.
- Income concentration.
- Largest income-producing holding.

This answers:

> Based on what I own today and what I currently expect each holding to produce, how much income should this portfolio generate over the next year, and what changed?

### 5.11 Forward Income Review

**Status: COMPLETE**

RIMS can consume the forward-income report and identify exceptions requiring attention.

Examples include:

- New Position.
- Position Change.
- Dividend Change.
- Position & Dividend Change.
- Position Closed.
- Forward Annual Income Missing.

"No Change" items are intentionally omitted from the review.

The review layer does not make investment recommendations.

This answers:

> What requires my attention?

---

## 6. Major Gap Identified

### RIMS Application / User Interface

**Status: NOT IMPLEMENTED**

The most significant remaining gap is not another analytical calculation.

It is the absence of a practical user-facing application layer.

The current system contains analytical capabilities that are individually usable by Python code, but the user does not yet have a unified workflow for operating RIMS.

The system needs an application layer that connects:

    Data Intake
         ↓
    Validation / Reconciliation
         ↓
    Portfolio Analysis
         ↓
    Historical Analysis
         ↓
    Forward Income
         ↓
    Review
         ↓
    Dashboard / Reports

---

## 7. Required User Workflow

The eventual RIMS application should allow the user to perform a periodic update without understanding the underlying Python modules.

The intended workflow is:

1. Open RIMS.
2. Import new Schwab reports.
3. RIMS validates the files.
4. RIMS identifies the reporting date.
5. RIMS imports the data.
6. RIMS reconciles the portfolio.
7. RIMS preserves the historical record.
8. RIMS updates current portfolio information.
9. RIMS calculates current income information.
10. RIMS updates forward-income information.
11. RIMS identifies changes.
12. RIMS identifies items requiring attention.
13. RIMS presents the results through the Dashboard.

The user should not need to manually execute individual analytical modules.

---

## 8. Dashboard Requirements

The Dashboard should eventually answer the four original success questions within approximately one minute.

At minimum, the Dashboard should provide:

### Portfolio Overview

- Total portfolio value.
- Securities value.
- Cash.
- Cost basis.
- Gain/loss.
- Holding count.

### Income Overview

- Forward annual income.
- Income target.
- Income surplus/shortfall when a target has been configured.
- Income concentration.
- Largest income-producing holdings.

### Attention Required

Display only items that require review, including:

- Dividend changes.
- Position changes.
- New positions.
- Closed positions.
- Missing forward-income assumptions.

### Historical View

Provide access to:

- Historical portfolio value.
- Historical forward income.
- Income trends.
- Significant portfolio changes.

### Reports

Provide access to generated RIMS reports without requiring the user to execute Python modules manually.

---

## 9. What Should NOT Be Added Yet

The following existing backlog items should remain deferred until the core application workflow is operational:

- Portfolio Health Score.
- Advisor Scorecard.
- Research & Opportunities.
- Stock Rover Integration.
- Dividend Calendar.
- Retirement Forecasting.
- Roth Conversion Planning.
- Tax Analysis.
- Income Stress Testing.
- AI Portfolio Review.

These capabilities may ultimately become important, but adding them before the core application is complete would increase complexity without solving the primary usability gap.

---

## 10. Architectural Direction

The application layer must not duplicate financial logic.

The intended architecture is:

    User Interface
          │
          ▼
    Application / Workflow Layer
          │
          ▼
    Existing RIMS Services
          │
          ├── Portfolio
          ├── Importer
          ├── Historical Analysis
          ├── Income Analysis
          ├── Forward Income
          ├── Forward Income Manager
          ├── Forward Income Report
          └── Forward Income Review
          │
          ▼
    Persistent RIMS Data

Financial calculations remain in the existing business-logic modules.

The Dashboard presents results produced by those modules.

This preserves separation of responsibilities and prevents business logic from migrating into the user interface.

---

## 11. Application Development Strategy

The application should be developed incrementally.

The first application sprint should NOT attempt to implement every Dashboard feature.

The initial application increment should establish:

- Application framework.
- Main entry point.
- Navigation structure.
- Dashboard shell.
- Data directory awareness.
- Error handling.
- Connection to existing RIMS services.

Subsequent sprints can then add:

- Data import workflow.
- Portfolio Dashboard.
- Income Dashboard.
- Review Dashboard.
- Historical Dashboard.
- Report presentation.

This keeps the application architecture manageable and allows each increment to be tested independently.

---

## 12. Gap Summary

| Capability | Assessment |
|---|---|
| Core data model | Complete |
| Schwab import | Complete foundation |
| Portfolio reconciliation | Complete |
| Current portfolio analysis | Complete |
| Historical snapshots | Complete |
| Historical comparison | Complete |
| Historical income trend | Complete foundation |
| Transaction history | Complete foundation |
| Historical income analysis | Complete foundation |
| Forward-income assumptions | Complete foundation |
| Forward-income management | Complete foundation |
| Forward-income reporting | Complete |
| Forward-income review | Complete |
| User-facing application | **Missing** |
| Dashboard | **Missing** |
| Periodic data-import workflow | **Missing** |
| Integrated report presentation | **Missing** |
| Goals/configuration presentation | Partial |
| Advisor workflow | Deferred |
| Research workflow | Deferred |
| Tax/RMD workflow | Deferred |
| Retirement forecasting | Deferred |
| Stress testing | Deferred |

---

## 13. Sprint 19P Decision

The assessment establishes that the current RIMS architecture has reached the point where continued development should shift from primarily adding analytical engines to building the application layer that integrates those engines.

The next major development increment should therefore be:

## Sprint 20 — RIMS Application Foundation

### Objective

Establish the user-facing RIMS application framework and Dashboard shell without duplicating existing financial business logic.

### Initial Scope

- Application framework.
- Main application entry point.
- Dashboard shell.
- Navigation structure.
- Integration points for existing RIMS services.
- Basic error handling.
- Preparation for periodic report/file ingestion.

### Explicitly Out of Scope

- Investment recommendations.
- Tax planning.
- RMD optimization.
- Advisor scoring.
- Research integration.
- Stress testing.
- AI portfolio review.
- Advanced forecasting.

These capabilities remain backlog items until the core application workflow is operational.

---

## 14. Guiding Principle

The Sprint 19P review reinforces the following RIMS principle:

> **Complexity belongs in the software, not with the user.**

The user should interact with RIMS in terms of:

- What do I own?
- How much income should it produce?
- What changed?
- What requires my attention?
- How am I doing over time?
- What should I discuss with my advisor?

The underlying software should handle:

- Imports.
- Reconciliation.
- Historical storage.
- Calculations.
- Forward-income assumptions.
- Change detection.
- Review logic.
- Report generation.

---

## 15. Acceptance Criteria

Sprint 19P is complete when:

- The original RIMS objectives have been reviewed.
- Current capabilities have been assessed.
- Significant gaps have been identified.
- The application/dashboard gap has been explicitly documented.
- Deferred capabilities have been identified.
- Sprint 20 direction has been established.
- No production financial logic has been changed.

---

## 16. Result

Sprint 19P establishes a controlled transition from the analytical foundation phase of RIMS to the application phase.

Sprints 1–19O established the core data, income, historical, forward-income, reporting, and review capabilities.

Sprint 20 should begin integrating those capabilities into a practical RIMS application.

The next development question is therefore no longer:

> What analytical capability should RIMS add next?

It is:

> How should RIMS turn the capabilities already built into a simple, reliable workflow for periodic retirement-portfolio management?

That question defines the beginning of the RIMS application phase.
