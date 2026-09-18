# RIMS Change Log

All significant RIMS development work is organized by numbered sprint.

Each sprint represents a controlled development increment and includes:

- Objective
- Files changed
- Implementation
- Testing
- Completion status

The Git repository is the authoritative source for the current implementation.
This change log provides the corresponding development history.

---

## Sprint 1 — Project Definition

**Status:** Complete

**Objective:**
Establish the RIMS project definition, purpose, scope, and development direction.

**Completed:**
- Defined Retirement Income Management System (RIMS).
- Established retirement-income management as the primary objective.
- Defined capital preservation as a secondary objective.
- Established a long-term investment horizon.
- Established the initial system-development approach.

---

## Sprint 2 — Project Architecture

**Status:** Complete

**Objective:**  
Define the initial RIMS architecture, project structure, core entities, and system-of-record philosophy.

**Completed:**
- Defined the RIMS project structure.
- Established core entities:
  - Portfolio
  - Holding
  - Snapshot
  - Configuration
  - Workbook
  - Watch List
  - Report
- Established Schwab as the system of record for holdings, market values, cost basis, and transactions.
- Established RIMS as the system of record for derived analysis, goals, notes, watch status, and historical analysis.
- Established configuration-driven business rules.
- Established the principle that historical data must never be overwritten.

---

## Sprint 3 — Change Management

**Status:** Complete

**Objective:**  
Establish formal project change tracking and version history.

**Completed:**
- Created `CHANGELOG.md`.
- Established version/change tracking.
- Established the practice of documenting significant development changes.

---

## Sprint 4 — Repository Configuration

**Status:** Complete

**Objective:**  
Establish repository hygiene and protect local/project data from accidental Git commits.

**Files changed:**
- `.gitignore`

**Completed:**
- Added RIMS data directories to Git exclusions.
- Added local configuration exclusions.
- Added macOS system-file exclusions.
- Added temporary-file exclusions.

---

## Sprint 5 — Runtime Dependencies

**Status:** Complete

**Objective:**  
Define the initial Python runtime dependencies.

**Files changed:**
- `requirements.txt`

**Completed:**
- Established Python 3.12+ requirement.
- Added NumPy.
- Added pandas.
- Added openpyxl.
- Added python-dateutil.
- Established bounded dependency versions.

---

## Sprint 6 — Build Entry Point

**Status:** Complete

**Objective:**  
Create the initial RIMS build/runtime entry point.

**Files changed:**
- `build_rims.py`

**Completed:**
- Added RIMS version reporting.
- Added Python version reporting.
- Added project-root identification.
- Added basic build-status reporting.
- Verified successful execution under Python 3.14.6.

---

## Sprint 7 — Application Package

**Status:** Complete

**Objective:**  
Establish the RIMS Python application package.

**Files changed:**
- `src/__init__.py`

**Completed:**
- Defined the `src` package.
- Added package-level version metadata.
- Established RIMS version 0.2.0.

---

## Sprint 8 — Holding Entity

**Status:** Complete

**Objective:**  
Create the core RIMS Holding entity.

**Files changed:**
- `src/holding.py`

**Completed:**
- Added Holding data model.
- Added shares, price, cost basis, dividend, and classification fields.
- Added market-value calculation.
- Added gain/loss calculation.
- Added gain/loss percentage.
- Added forward annual dividend income.
- Added portfolio yield.
- Added income yield on cost.
- Added price and dividend update methods.
- Added dictionary serialization.
- Established forward annual dividend income as the primary income metric.

---

## Sprint 9 — Portfolio Entity

**Status:** Complete

**Objective:**  
Create the RIMS Portfolio aggregation layer.

**Files changed:**
- `src/portfolio.py`

**Completed:**
- Added portfolio holding management.
- Added duplicate-symbol validation.
- Added portfolio market value.
- Added portfolio cost basis.
- Added total gain/loss.
- Added forward annual dividend income.
- Added portfolio yield.
- Added income yield on cost.
- Added position-weight calculations.
- Added income-contribution calculations.
- Added portfolio serialization.

**Testing:**
- Verified portfolio aggregation using test Holdings.
- Verified market value, cost basis, gain/loss, income, yield, position weight, and income contribution.

---

## Sprint 10 — Schwab CSV Import and Reconciliation

**Status:** Complete

**Objective:**  
Import Schwab position data into RIMS and reconcile the imported portfolio against Schwab.

**Files changed:**
- `src/importer.py`

**Completed:**
- Added Schwab CSV parsing.
- Added support for multiple Schwab account sections.
- Added security-row identification.
- Added cash-row identification.
- Added summary-row handling.
- Added Schwab date parsing.
- Added Schwab numeric-value parsing.
- Added duplicate-symbol consolidation.
- Added Schwab market-value totals.
- Added Schwab cost-basis totals.
- Added reconciliation status.
- Added market-value and cost-basis differences.
- Added reconciliation tolerance.

**Validation:**
- 45 securities imported.
- Schwab securities value: $754,211.09.
- Schwab cash: $45,016.45.
- Schwab total value: $799,227.54.
- Cost basis reconciled to $793,924.63.
- Forward annual dividend income: $53,581.31.
- Portfolio yield: 7.10%.
- Reconciliation status: RECONCILED.

---

## Sprint 11 — Authoritative Schwab Market Values

**Status:** Complete

**Objective:**  
Make Schwab's reported market value authoritative within RIMS while retaining calculated market value for validation and fallback purposes.

**Files changed:**
- `src/holding.py`
- `src/importer.py`

**Completed:**
- Added authoritative `market_value` support to Holding.
- Retained calculated market value as `shares × price`.
- Added `calculated_market_value` for comparison and validation.
- Added market-value update capability.
- Preserved calculated market-value fallback for manually created Holdings.
- Updated Schwab importer to pass Schwab market value into Holding.
- Updated duplicate-security consolidation to sum authoritative market values.
- Corrected Schwab cash and summary-row classification.

**Validation:**
- Holding fallback test: PASS.
- Authoritative market-value test: PASS.
- Schwab import regression test: PASS.
- 45 securities imported.
- RIMS securities value: $754,211.09.
- Schwab securities value: $754,211.09.
- Schwab cash: $45,016.45.
- Schwab total value: $799,227.54.
- Cost basis difference: $0.00.
- Market value difference: $0.00.
- Forward annual dividend income: $53,581.31.
- Portfolio yield: 7.10%.
- Reconciliation status: RECONCILED.
- EMHY multi-account consolidation verified:
  - 497 shares.
  - $19,125.50 cost basis.
  - $20,210.51 authoritative market value.
  - $1,322.4673 forward annual dividend income.

---

## Development Rules Going Forward

Every future development increment will be assigned a sequential sprint number.

Each sprint will:

1. Have a clearly defined objective.
2. Identify the files changed.
3. Be tested before completion.
4. Be committed to Git.
5. Be pushed to GitHub.
6. Be recorded in this change log.

Sprint numbers will not be reused or skipped.

---

## Sprint 12 — Historical Portfolio Snapshot

**Status:** Complete

**Objective:**
Create the first version of historical portfolio snapshot capability.

**Files Added:**
- `src/snapshot.py`

**Implementation:**
- Added `Snapshot` dataclass for point-in-time portfolio history.
- Snapshot captures portfolio metrics at a specific date.
- Captures securities market value separately from cash market value.
- Calculates total portfolio market value including cash.
- Captures cost basis, gain/loss, forward annual dividend income, portfolio yield, and income yield on cost.
- Preserves individual holding information.
- Uses independent copies of holdings so subsequent changes to the live Portfolio do not alter the historical Snapshot.
- Added dictionary serialization through `to_dict()`.

**Testing:**
- Snapshot module import test passed.
- Snapshot creation test passed.
- Financial metric validation passed.
- Cash handling validated.
- Snapshot independence from live Portfolio validated.
- Individual holding preservation validated.
- Dictionary serialization validated.
- Existing Schwab import and reconciliation regression test passed.

**Acceptance:**
- Historical Snapshot capability implemented and tested.
- Existing RIMS functionality remains operational.
- Schwab market value and cost basis reconciliation remain exact.

**Result:**
Sprint 12 complete. Historical portfolio snapshot capability is ready for subsequent integration and historical analysis work.

---

## Sprint 13 — Historical Snapshot Storage

**Status:** Complete

**Objective:**

Add persistent storage and retrieval for RIMS historical portfolio Snapshots using JSON files.

**Files Added:**

- `src/snapshot_store.py`

**Implementation:**

- Added `SnapshotStore` for persistent historical Snapshot storage.
- Stores each Snapshot as an individual JSON file using the Snapshot date as the filename.
- Automatically creates the configured Snapshot storage directory when needed.
- Loads previously saved Snapshots back into RIMS `Snapshot` and `Holding` objects.
- Lists available historical Snapshot dates in chronological order.
- Prevents accidental overwriting of an existing Snapshot by default.
- Allows intentional replacement when `overwrite=True` is explicitly specified.
- Preserves Decimal financial values and date values during JSON serialization and reconstruction.
- Maintains the authoritative historical holding market value when Snapshots are reconstructed.

**Testing:**

- SnapshotStore module import test passed.
- Snapshot successfully saved to JSON.
- Snapshot successfully loaded from JSON.
- Historical financial metrics preserved through save/load round trip.
- Individual holdings successfully reconstructed.
- Multiple historical Snapshot dates successfully listed.
- Accidental overwrite protection validated.
- Intentional overwrite validated.
- Existing RIMS functionality remains unaffected.

**Acceptance:**

- Historical Snapshots can be persistently stored.
- Stored Snapshots can be retrieved and reconstructed.
- Multiple historical Snapshot dates can be maintained.
- Existing historical records are protected from accidental replacement.
- Existing RIMS functionality remains operational.

**Result:**

Sprint 13 complete. Persistent JSON storage for historical portfolio Snapshots is operational and ready to support future historical analysis.

## Sprint 14 — Historical Snapshot Comparison

**Status:** Complete

**Objective:**
Create the first RIMS capability for comparing two historical portfolio snapshots and quantifying changes in portfolio value, income, and individual holdings.

**Implementation:**
- Added `src/snapshot_comparison.py`.
- Added `HoldingChange` for security-level comparisons.
- Added `SnapshotComparison` for portfolio-level comparisons.
- Added comparison of total market value, securities value, cash, cost basis, gain/loss, forward annual dividend income, portfolio yield, income yield on cost, and holding count.
- Added identification of common, added, and removed holdings.
- Added holding-level changes for shares, market value, cost basis, gain/loss, and forward annual dividend income.
- Used forward annual dividend income in dollars as the primary income comparison metric.
- Portfolio yield and income yield on cost are reported as changes in percentage points.
- Preserved Decimal precision for financial calculations.
- Added dictionary serialization of comparison results.
- Preserved historical snapshot independence.
- Explicitly excluded investment performance and total return calculations because transaction history is not yet integrated.

**Testing:**
- Snapshot comparison module import test passed.
- Portfolio-level comparison test passed.
- Added/removed/common holding test passed.
- Snapshot independence test passed.
- Identical snapshot/no-change test passed.
- Serialization test passed.
- Schwab import regression test passed.
- Schwab securities value reconciled to `$754,211.09`.
- Schwab cash reconciled to `$45,016.45`.
- Schwab total value reconciled to `$799,227.54`.
- Schwab cost basis reconciled to `$793,924.63`.
- Market value difference: `$0.00`.
- Cost basis difference: `$0.00`.
- Forward annual dividend income: `$53,581.31`.
- Portfolio yield: `7.10%`.

**Acceptance:**
All Sprint 14 acceptance criteria satisfied.

**Git:**
Code and documentation ready for commit and push.

## Sprint 15 — Historical Snapshot Reporting

**Status:** Complete

**Objective:**
Create the first RIMS human-readable reporting capability built on the historical snapshot comparison engine.

**Implementation:**
- Added `src/snapshot_report.py`.
- Added human-readable portfolio comparison reporting.
- Added portfolio market-value, securities-value, cash, cost-basis, gain/loss, and holding-count reporting.
- Added prominent forward annual dividend income reporting.
- Added portfolio yield and income yield on cost reporting.
- Reported yield changes as percentage-point changes.
- Added common, added, and removed holding reporting.
- Added holding-level changes for shares, market value, cost basis, gain/loss, and forward annual dividend income.
- Added identification of the largest positive and negative changes in forward annual dividend income.
- Preserved the distinction between market-value change and investment performance.
- Excluded total-return and investment-performance calculations because transaction history is not yet integrated.
- Corrected percentage formatting to match the RIMS percentage representation used by the existing Snapshot and Portfolio models.

**Testing:**
- SnapshotReport module import test passed.
- Normal portfolio comparison report test passed.
- Added/removed holding report test passed.
- Income-impact ranking test passed.
- No-change report test passed.
- Percentage formatting defect identified and corrected.
- Corrected percentage formatting test passed.
- Schwab import regression test passed.
- Schwab securities value reconciled to `$754,211.09`.
- Schwab cash reconciled to `$45,016.45`.
- Schwab total value reconciled to `$799,227.54`.
- Schwab cost basis reconciled to `$793,924.63`.
- Market value difference: `$0.00`.
- Cost basis difference: `$0.00`.
- Forward annual dividend income: `$53,581.31`.
- Portfolio yield: `7.10%`.

**Acceptance:**
All Sprint 15 acceptance criteria satisfied.

**Git:**
Code and documentation ready for commit and push.

## Sprint 16 — Historical Analysis Orchestration

**Status:** Complete

**Objective:**
Connect the historical snapshot components into an end-to-end RIMS workflow without duplicating business logic in the orchestration layer.

**Implementation:**
- Added `src/historical_analysis.py`.
- Added orchestration for creating historical snapshots from portfolios.
- Added snapshot persistence through `SnapshotStore`.
- Added historical snapshot retrieval by date.
- Added listing of available snapshot dates.
- Added comparison of stored historical snapshots.
- Added generation of human-readable historical reports from stored snapshots.
- Added direct comparison and reporting methods for Snapshot objects already held in memory.
- Kept financial calculations within the existing Portfolio, Snapshot, SnapshotComparison, and related classes.
- Preserved the separation between orchestration and core business logic.
- Preserved existing overwrite protection through SnapshotStore.

**Testing:**
- HistoricalAnalysis module import test passed.
- End-to-end Portfolio → Snapshot → SnapshotStore → Load → SnapshotComparison → SnapshotReport workflow passed.
- Snapshot 1 saved successfully for `2026-07-31`.
- Snapshot 2 saved successfully for `2026-08-31`.
- Stored snapshot retrieval returned the expected holding count.
- Snapshot date listing returned both historical dates.
- Market value change calculated correctly at `$520`.
- Forward annual dividend income change calculated correctly at `$21.00`.
- Holding count change calculated correctly at `0`.
- Complete historical report generated correctly.
- Temporary test data removed after testing.
- Existing production functionality remains unchanged.

**Acceptance:**
All Sprint 16 acceptance criteria satisfied.

**Git:**
Code and documentation ready for commit and push.

## Sprint 17 — Historical Income Trend
**Status:** Complete
**Objective:**
Create the first RIMS capability for analyzing forward annual dividend income across multiple historical portfolio snapshots.

**Implementation:**
- Added `src/income_trend.py`.
- Added `IncomeObservation` for historical income observations.
- Added `IncomeChange` for period-to-period income changes.
- Added `IncomeTrend` for multi-snapshot historical income analysis.
- Added chronological ordering of historical snapshots.
- Added beginning-to-ending forward annual dividend income analysis.
- Added period-to-period income changes in dollars.
- Added income percentage-change calculations.
- Added portfolio-yield changes in percentage points.
- Added income-yield-on-cost changes in percentage points.
- Added portfolio market-value changes for context.
- Added Increasing, Decreasing, and Stable trend classification.
- Added identification of the largest income increase and decrease.
- Added validation for empty snapshots, duplicate dates, and mixed portfolios.
- Added dictionary serialization of trend results.
- Kept forward annual dividend income in dollars as the primary income metric.
- Preserved the distinction between income changes and investment performance.
- Did not introduce CAGR, total-return, or performance calculations because transaction history is not yet integrated.

**Testing:**
- IncomeTrend module import test passed.
- Three-snapshot increasing-income test passed.
- Chronological ordering test passed.
- Period-to-period income calculation test passed.
- Overall income change test passed.
- Income percentage-change test passed.
- Increasing trend classification test passed.
- Decreasing trend classification test passed.
- Stable trend classification test passed.
- Largest income increase test passed.
- Largest income decrease test passed.
- One-snapshot edge case passed.
- Zero-snapshot rejection test passed.
- Different portfolio validation test passed.
- Duplicate snapshot-date validation test passed.
- Serialization test passed.
- Python compile test passed.
- Schwab import regression test passed.
- Schwab securities value reconciled to `$754,211.09`.
- Schwab cash reconciled to `$45,016.45`.
- Schwab total value reconciled to `$799,227.54`.
- Schwab cost basis reconciled to `$793,924.63`.
- Market value difference: `$0.00`.
- Cost basis difference: `$0.00`.
- Forward annual dividend income: `$53,581.31`.
- Portfolio yield: `7.10%`.
- First permanent historical snapshot created for `2026-06-29`.
- Permanent snapshot contains 45 holdings and `$53,581.305272` forward annual dividend income.
- Permanent snapshot save/load verification passed.

**Acceptance:**
All Sprint 17 acceptance criteria satisfied.

**Git:**
Code and documentation ready for commit and push.

## Sprint 18 — Portfolio Income Analysis

### Objective
Implement portfolio-level analysis answering:

> Where is my retirement income coming from?

The primary metric is forward annual dividend income in dollars. Yield remains a supporting metric for screening and relative analysis.

### Implementation
- Added `src/income_analysis.py`.
- Added holding-level annual dividend income analysis.
- Added income contribution percentage for each holding.
- Added income ranking from highest to lowest income producer.
- Added top 1, 3, 5, and 10 income concentration analysis.
- Added aggregate income analysis by asset type.
- Added aggregate income analysis by sector.
- Added market-value concentration alongside income concentration.
- Added configurable minimum-yield screening.
- Added configurable high-yield review screening.
- Default minimum yield: 5%.
- Default high-yield review threshold: 10%.
- High-yield screening is a review flag only and does not constitute a sell recommendation.
- Added portfolio-level income, yield, and income-yield-on-cost metrics.
- Added serialization through `to_dict()`.
- Calculations use `Decimal`.
- Analysis does not modify the underlying portfolio or holdings.

### Importer Integration
Updated `src/importer.py` so Schwab rows identified as `Cash and Money Market` are excluded from security holdings and included in the portfolio's separate cash value.

This prevents cash and money-market positions from being treated as dividend-producing securities.

### Testing
Validated:
- Module import.
- Holding-level income calculations.
- Income contribution percentages.
- Top income concentration.
- Asset-type aggregation.
- Sector aggregation.
- Minimum-yield screening.
- High-yield review screening.
- Configurable thresholds.
- Zero-income portfolio handling.
- Empty portfolio handling.
- No-mutation behavior.
- Dictionary serialization.
- Actual Schwab portfolio regression.
- Snapshot integration.
- Python compilation.
- Git whitespace validation.

### Schwab Regression Results
Using the actual Schwab position export:

- Holdings: 44 securities.
- Securities market value: $742,729.23.
- Cash and money market: $56,498.31.
- Total portfolio value: $799,227.54.
- Securities cost basis: $782,442.77.
- Forward annual dividend income: $53,177.1438.
- Regression status: PASS.

The change correctly reclassified SWVXX as cash rather than a security holding.

### Acceptance
Sprint 18 acceptance criteria completed.

### Git
Sprint 18 implementation and related importer correction are ready for commit and push after final verification.
## Sprint 19A — Investment Transaction Model

**Status:** Complete

**Objective:**

Establish the normalized RIMS investment transaction model required to preserve historical transaction activity and support future income and performance analysis.

**Files added:**

- `src/transaction.py`

**Implementation:**

- Added `InvestmentTransaction` data model.
- Added transaction date, action, symbol, description, amount, quantity, price, fees, and account fields.
- Added transaction-type classification.
- Added income-type classification:
  - Dividend
  - Interest
  - Capital Gain Distribution
  - Other
- Added income-character classification:
  - Recurring
  - Special
  - Reinvested
  - Prior Year
  - Adjustment
- Added tax-character classification.
- Allowed transactions without security symbols to support items such as bank interest.
- Added authoritative transaction-level income classification.
- Added recurring-income determination.
- Added explicit capital-gain-distribution identification.
- Preserved the distinction between income and purchase transactions.

**Income handling:**

- Reinvested dividends are treated as income.
- Reinvest Shares transactions are treated as purchases and are not counted as additional income.
- Capital-gain distributions remain visible but are excluded from recurring retirement income.

**Result:**

Sprint 19A complete. The normalized transaction model provides the foundation for historical transaction storage and income analysis.

---

## Sprint 19B — Schwab Income Transaction Importer

**Status:** Complete

**Objective:**

Import Schwab historical income transactions into the normalized RIMS transaction model while preserving the original transaction information and account identity.

**Files added:**

- `src/schwab_income_importer.py`

**Implementation:**

- Added Schwab transaction CSV import for income-related transactions.
- Preserved the Schwab source action and description.
- Preserved account identity.
- Preserved optional security symbols.
- Converted Schwab dates and financial amounts into RIMS types.
- Classified Schwab actions into RIMS transaction, income, and income-character categories.
- Preserved source-file provenance.
- Added support for multiple Schwab income transaction files.

**Income classification:**

- Cash dividends classified as dividend income.
- Qualified and non-qualified dividends preserved through tax-character classification.
- Bond interest classified as interest income.
- Bank interest supported without a security symbol.
- Special dividends identified as special income.
- Prior-year income identified separately.
- Dividend adjustments identified separately.
- Capital-gain distributions preserved but excluded from recurring retirement income.
- Reinvested income preserved as income.
- Reinvest Shares transactions excluded from income totals.

**Validation:**

- Actual Schwab income transaction exports successfully imported.
- Account identity preserved.
- Source-file provenance preserved.
- Transaction classifications validated against Schwab source actions.

**Result:**

Sprint 19B complete. RIMS can now convert Schwab historical income transactions into the normalized transaction model.

---

## Sprint 19C — Multi-Account Income Aggregation

**Status:** Complete

**Objective:**

Create the analytical layer that combines normalized income transactions across multiple accounts while preserving account and transaction identity.

**Files added:**

- `src/income_aggregation.py`

**Implementation:**

- Added `IncomeAggregationResult`.
- Added aggregation across multiple accounts.
- Added total historical income.
- Added recurring historical income.
- Added special-income totals.
- Added reinvested-income totals.
- Added prior-year income totals.
- Added income-adjustment totals.
- Added capital-gain-distribution totals.
- Added income breakdown by account.
- Added income breakdown by security symbol.
- Added income breakdown by income type.
- Added income breakdown by income character.
- Added income breakdown by year.
- Added income breakdown by date.
- Preserved transactions within the aggregation result for further analysis.
- Used deterministic transaction ordering.
- Preserved symbolless income such as bank interest.
- Explicitly limited the aggregation layer to actual historical transactions.

**Design principle:**

The aggregation layer does not project future dividend payments or annualize partial periods.

**Result:**

Sprint 19C complete. RIMS can now aggregate historical income across all imported accounts without losing account-level identity.

---

## Sprint 19D — Historical Income Analysis

**Status:** Complete

**Objective:**

Create historical income analysis based on actual imported transactions, including annual summaries and recurring-income trends.

**Files added:**

- `src/historical_income.py`

**Implementation:**

- Added `IncomeYearSummary`.
- Added `IncomeTrend`.
- Added `HistoricalIncomeResult`.
- Added historical income summaries by calendar year.
- Added recurring-income summaries by year.
- Added special-income summaries.
- Added prior-year income summaries.
- Added income-adjustment summaries.
- Added capital-gain-distribution summaries.
- Added income analysis by account.
- Added income analysis by symbol.
- Added income analysis by income type.
- Added year-over-year recurring-income trend analysis.
- Added dollar change calculations.
- Added percentage-change calculations.
- Identified partial current years.
- Preserved actual transaction amounts without annualization or projection.

**Design principle:**

Historical income analysis reports actual transaction facts. It does not project future income or annualize a partial year.

**Result:**

Sprint 19D complete. RIMS can now analyze historical income by year, account, security, and income type and identify historical recurring-income trends.

---

## Sprint 19E — Historical Transaction Persistence

**Status:** Complete

**Objective:**

Persist normalized historical investment transactions so that imported historical data can be retained and queried without re-importing Schwab files.

**Files added:**

- `src/transaction_store.py`

**Files updated:**

- `.gitignore`

**Implementation:**

- Added `TransactionDataset`.
- Added `TransactionStore`.
- Added JSON persistence for historical transaction datasets.
- Added dataset identification.
- Added account and source-file provenance to persisted datasets.
- Added transaction serialization and reconstruction.
- Preserved Decimal financial values.
- Preserved transaction dates.
- Preserved transaction classifications.
- Added dataset listing.
- Added dataset loading.
- Added accidental-overwrite protection.
- Added explicit overwrite capability when intentionally requested.
- Added local transaction-data exclusions to `.gitignore`.

**Design principle:**

Historical transaction records are persisted as historical facts and are not silently overwritten.

**Result:**

Sprint 19E complete. RIMS now has persistent historical transaction storage.

---

## Sprint 19F — Historical Transaction Repository

**Status:** Complete

**Objective:**

Create a RIMS-level repository interface for accessing persisted historical transaction datasets across multiple accounts.

**Files added:**

- `src/transaction_repository.py`

**Implementation:**

- Added `TransactionRepository`.
- Added repository construction from a storage path.
- Added dataset saving.
- Added dataset loading.
- Added persisted dataset discovery.
- Added loading of all datasets.
- Added combined transaction retrieval across accounts.
- Added deterministic chronological transaction ordering.
- Added account filtering.
- Added symbol filtering.
- Added date-range filtering.
- Added income-type filtering.
- Added transaction-type filtering.
- Added income transaction retrieval.
- Added recurring-income transaction retrieval.
- Added total historical income calculation.
- Added total recurring-income calculation.
- Added account discovery.
- Added symbol discovery.
- Preserved account identity and source-file provenance.

**Design principle:**

The repository provides access to persisted historical records without modifying the underlying transactions or duplicating Schwab import logic.

**Result:**

Sprint 19F complete. RIMS now has a repository abstraction between persistent transaction storage and higher-level analysis.

---

## Sprint 19G — Transaction Repository Hardening and Automated Tests

**Status:** Complete

**Objective:**

Harden the historical transaction repository and establish the first permanent automated regression test suite for the transaction infrastructure.

**Files changed:**

- `src/transaction_repository.py`
- `tests/test_transaction_repository.py`

**Implementation:**

- Added validation for blank account filters.
- Added validation for blank symbol filters.
- Added validation for invalid date ranges.
- Added validation for invalid date types.
- Added validation for invalid income types.
- Added validation for invalid transaction types.
- Added clearer handling of corrupt persisted JSON.
- Added clearer handling of structurally invalid persisted JSON.
- Preserved source-file provenance through repository load operations.
- Preserved deterministic transaction ordering.
- Preserved protection against accidental dataset overwrites.

**Testing:**

- Added automated repository regression tests.
- Verified account filtering.
- Verified symbol filtering.
- Verified date-range filtering.
- Verified income-type filtering.
- Verified transaction-type filtering.
- Verified income totals.
- Verified recurring-income totals.
- Verified special-income exclusion from recurring income.
- Verified empty repositories.
- Verified invalid input rejection.
- Verified corrupt JSON rejection.
- Verified missing required JSON data rejection.
- Verified source provenance preservation.
- **19 repository tests passed.**

**Real-data validation:**

Using the three actual Schwab income transaction exports:

- 779 total transactions.
- 751 income transactions.
- 674 recurring-income transactions.
- Total historical income: **$68,440.04**.
- Total recurring income: **$65,533.10**.

**Git:**

- Commit: `e9dae05`
- Repository hardening and automated tests pushed to GitHub.

**Result:**

Sprint 19G complete. The transaction repository is hardened and protected by a permanent automated regression suite.

---

## Sprint 19H — Historical Income Query Service

**Status:** Complete

**Objective:**

Create a convenient repository-backed service for querying historical income without duplicating aggregation logic, forecasting future income, or modifying historical transaction records.

**Files added:**

- `src/income_query.py`
- `tests/test_income_query.py`

**Implementation:**

- Added `IncomeQuery`.
- Added historical income queries by account.
- Added historical income queries by security symbol.
- Added historical income queries by income type.
- Added historical income queries by date range.
- Added historical income queries by calendar year.
- Added recurring-income filtering.
- Added special-income queries by year.
- Added reinvested-income queries by year.
- Added prior-year income queries by year.
- Added income-adjustment queries by year.
- Added capital-gain-distribution queries by year.
- Added total historical income.
- Added total recurring income.
- Added total special income.
- Added total reinvested income.
- Added total prior-year income.
- Added total income adjustments.
- Added total capital-gain distributions.
- Reused the transaction model's authoritative recurring-income classification.
- Prevented Reinvest Shares transactions from being counted as additional income.
- Preserved capital-gain distributions as visible historical income while excluding them from recurring income.
- Preserved actual transaction amounts without annualization or future projection.
- Added convenience construction through `query_historical_income()`.

**Testing:**

- Added 15 automated IncomeQuery tests.
- Verified empty repository behavior.
- Verified account queries.
- Verified recurring-income queries.
- Verified case-insensitive symbol queries.
- Verified income-type queries.
- Verified inclusive date ranges.
- Verified annual income queries.
- Verified recurring annual income queries.
- Verified special income.
- Verified reinvested income.
- Verified prior-year income.
- Verified income adjustments.
- Verified capital-gain distributions.
- Verified Reinvest Shares are not double-counted.
- Verified invalid input rejection.
- **34 total automated tests passed across Sprints 19G and 19H.**

**Real-data integration validation:**

Using the three actual Schwab income transaction exports:

- Total historical income: **$68,440.04**.
- Total recurring income: **$65,533.10**.
- 2025 income: **$32,852.46**.
- 2025 recurring income: **$31,964.78**.
- 2026 income: **$35,587.58**.
- 2026 recurring income: **$33,568.32**.
- Contributory ...111 recurring income: **$60,968.96**.
- Joint Tenant ...941 recurring income: **$3,151.48**.
- Roth Contributory IRA ...916 recurring income: **$1,412.66**.
- Dividend income: **$54,160.89**.
- Interest income: **$14,255.03**.
- Capital-gain distributions: **$24.12**.
- Special income: **$629.53**.
- Reinvested income: **$603.45**.
- Prior-year income: **$1,698.57**.
- Income adjustments: **-$48.68**.

All integration results reconciled to the previously established historical income totals.

**Git:**

- Commit: `7471a46`
- Historical income query service and automated tests pushed to GitHub.
- Working tree verified clean.
- Local `main` verified up to date with `origin/main`.

**Result:**

Sprint 19H complete. RIMS now has a repository-backed historical income query layer suitable for future reporting, income dashboards, and retirement-income analysis.

---

## Sprint 19I — Historical Income / Current Portfolio Reconciliation

**Objective:**

Reconcile historical income with the user's current portfolio so RIMS can distinguish income generated by securities still held from income generated by securities no longer held.

**Files added:**

- `src/income_portfolio.py`
- `tests/test_income_portfolio.py`
- `tests/test_income_portfolio_integration.py`

**Implementation:**

- Added historical income reconciliation against the current portfolio.
- Identified historical income generated by securities currently held.
- Identified recurring historical income generated by current holdings.
- Identified historical income generated by securities no longer held.
- Preserved symbolless historical income as a separate category.
- Reconciled the categories to total historical income without double counting.
- Used positive-share holdings as the definition of current holdings.
- Preserved the distinction between historical income and future income.
- Established a foundation for comparing historical income production with the current portfolio.

**Testing:**

- Added 17 automated unit tests.
- Added real-data integration testing.
- Verified current portfolio loading.
- Verified historical transaction repository integration.
- Verified current holdings versus previously held securities.
- Verified recurring-income reconciliation.
- Verified symbolless income treatment.
- Verified total-income reconciliation.
- **65 total automated tests passed across the complete test suite at sprint completion.**

**Real-data integration validation:**

Using the Schwab positions file dated September 7, 2026 and the three-account historical transaction repository:

- Current holdings: **42 positive-share holdings**
- Current portfolio market value: **$721,964.72**
- Historical income from current holdings: **$63,336.50**
- Recurring historical income from current holdings: **$61,155.51**
- Historical income from securities no longer held: **$5,016.21**
- Symbolless historical income: **$87.33**
- Reconciled total historical income: **$68,440.04**

Sprint 19I complete. RIMS can now reconcile historical income with the securities currently held in the portfolio without confusing historical income with future income.

---

## Sprint 19J — Current Income Position Analysis

**Objective:**

Create a current-portfolio income analysis layer showing how historical income is distributed across securities currently held, while avoiding annualization, projection, yield substitution, or double counting.

**Files added:**

- `src/current_income.py`
- `tests/test_current_income.py`
- `tests/test_current_income_integration.py`

**Implementation:**

- Added `CurrentHoldingIncome`.
- Added `CurrentIncomeResult`.
- Calculated historical income for each current holding.
- Calculated recurring historical income for each current holding.
- Calculated each holding's percentage contribution to recurring income.
- Identified current holdings with and without historical income.
- Calculated total current market value.
- Calculated total historical income from current holdings.
- Calculated total recurring income from current holdings.
- Calculated income concentration.
- Preserved symbolless historical income separately.
- Excluded zero-share positions from current holdings.
- Prevented Reinvest Shares transactions from being counted as additional income.
- Preserved actual historical transaction amounts without annualization.
- Did not substitute current yield for historical income.
- Did not project historical income into the future.
- Did not mutate portfolio or transaction data.

**Testing:**

- Added 18 automated unit tests.
- Added real-data integration testing.
- Verified current holdings and positive-share filtering.
- Verified historical and recurring income calculations.
- Verified income concentration.
- Verified holdings without historical income.
- Verified symbolless income treatment.
- Verified no annualization or projection.
- Verified no double counting of reinvested income.
- **84 total automated tests passed across the complete test suite at sprint completion.**

**Real-data integration validation:**

Using the September 7, 2026 Schwab positions file:

- Current portfolio market value: **$721,964.72**
- Historical income from current holdings: **$63,336.50**
- Recurring historical income from current holdings: **$61,155.51**
- Holdings with historical income: **41**
- Holdings without historical income: **1**
- Largest individual holding contribution to recurring income: **4.62%**
- Top five holdings produced approximately **20.0%** of recurring income.
- Top ten holdings produced approximately **36.8%** of recurring income.
- RWAY represented approximately **1.81%** of recurring income.

Sprint 19J complete. RIMS now provides a current-position view of historical income production and income concentration without incorrectly treating historical results as future income.

---

## Sprint 19K — Forward Income Foundation

**Objective:**

Establish the architectural foundation for forward annual income analysis using only explicit income assumptions, without silently converting historical income into projected income.

**Files added:**

- `src/forward_income.py`
- `tests/test_forward_income.py`
- `tests/test_forward_income_integration.py`

**Implementation:**

- Added `ForwardIncomeAssumption`.
- Added `ForwardHoldingIncome`.
- Added `ForwardIncomeResult`.
- Added explicit forward annual income assumptions by security.
- Added effective dates for forward-income assumptions.
- Added source attribution for forward-income assumptions.
- Added notes for forward-income assumptions.
- Restricted forward-income analysis to explicit assumptions.
- Included only current holdings with positive shares.
- Calculated each holding's percentage contribution to forward income.
- Identified holdings with and without forward-income assumptions.
- Calculated total forward annual income.
- Calculated income concentration.
- Preserved market value separately from forward income.
- Explicitly prevented historical income from being silently converted into forward income.
- No annualization of historical income.
- No yield substitution.
- No unsupported income projection.

**Testing:**

- Added 17 automated unit tests.
- Added real-data integration testing.
- Verified explicit forward-income assumptions.
- Verified current positive-share holdings.
- Verified holdings without forward assumptions.
- Verified income concentration.
- Verified that historical income is not automatically treated as forward income.
- **102 total automated tests passed across the complete test suite at sprint completion.**

**Real-data integration validation:**

The integration test used three controlled forward-income assumptions:

- PFLT: **$2,800**
- BXSL: **$2,500**
- ARCC: **$2,000**
- Total explicit forward income: **$7,300**
- Current positive-share holdings: **42**
- Holdings without explicit forward-income assumptions: **39**
- Current portfolio market value: **$721,964.72**

Sprint 19K complete. RIMS now has a controlled foundation for forward-income analysis that keeps explicit future-income assumptions separate from historical income.

---

## Sprint 19L — Forward Income Persistence

**Objective:**

Provide persistent local storage for explicit forward annual income assumptions while protecting the user's actual financial data from accidental inclusion in the GitHub repository.

**Files added:**

- `src/forward_income_store.py`
- `tests/test_forward_income_store.py`

**Files modified:**

- `.gitignore`

**Implementation:**

- Added `ForwardIncomeStore`.
- Added persistent JSON storage for forward annual income assumptions.
- Added loading of persisted forward-income assumptions.
- Preserved `Decimal` precision when storing and loading income amounts.
- Preserved effective dates.
- Preserved source attribution.
- Preserved notes.
- Created the storage directory automatically when saving.
- Returned an empty tuple when no persisted dataset exists.
- Validated persisted JSON structure.
- Rejected invalid JSON record fields.
- Rejected invalid decimal values.
- Rejected invalid dates.
- Rejected duplicate security symbols.
- Rejected invalid assumption objects.
- Required tuple-based assumption collections for storage.
- Prevented accidental tracking of `data/forward_income/` by Git.
- Kept actual forward-income data separate from source code and tests.

**Testing:**

- Added 17 automated unit tests.
- Verified save/load round trips.
- Verified decimal precision preservation.
- Verified date, source, and notes preservation.
- Verified directory creation.
- Verified invalid input rejection.
- Verified duplicate-symbol rejection.
- Verified malformed persisted data rejection.
- **119 total automated tests passed across the complete test suite at sprint completion.**

Sprint 19L complete. RIMS can now persist explicit forward-income assumptions locally while keeping those personal financial data files outside the GitHub repository.

---

## Sprint 19M — Forward Income Position Management

**Objective:**

Extend the forward-income foundation so RIMS can automatically recognize changes in a current holding's position and expected income rate while presenting the results in simple, user-understandable terms.

**Files added:**

- `src/forward_income_change.py`
- `src/forward_income_baseline.py`
- `src/forward_income_manager.py`
- `tests/test_forward_income_change.py`
- `tests/test_forward_income_baseline.py`
- `tests/test_forward_income_manager.py`

**Files modified:**

- `src/forward_income.py`
- `tests/test_forward_income.py`
- `tests/test_forward_income_integration.py`

**Implementation:**

- Kept **Forward Annual Income** as the primary user-facing income concept.
- Internally represented forward income as an expected annual income amount per share or unit.
- Calculated forward annual income from current shares multiplied by the explicit forward income rate.
- Preserved the separation between historical income and explicit forward-income assumptions.
- Added automatic comparison of the current position against the previous baseline.
- Added automatic recognition of position changes.
- Added automatic recognition of expected income-rate changes.
- Added recognition of simultaneous position and expected income-rate changes.
- Added recognition of new positions.
- Added recognition of closed positions.
- Added recognition of positions with no change.
- Added simple user-facing change reasons:
  - **New Position**
  - **Position Change**
  - **Dividend Change**
  - **Position & Dividend Change**
  - **Position Closed**
  - **No Change**
- Added persistent baseline storage for the last known active forward-income positions.
- Added a management service to coordinate assumptions, current holdings, change detection, and baseline updates.
- Designed closed positions to appear once with **Position Closed** and then disappear from subsequent reports.
- Kept full historical change/audit tracking outside the scope of this sprint.
- Kept the user-facing model intentionally simple: a holding has shares and an expected annual income, and RIMS identifies what changed.

**Testing:**

- Added automated tests for change classification.
- Added automated tests for baseline persistence.
- Added automated tests for forward-income management.
- Verified new-position detection.
- Verified position-change detection.
- Verified dividend-change detection.
- Verified combined position-and-dividend change detection.
- Verified closed-position detection.
- Verified no-change detection.
- Verified that closed positions appear only on the closing report.
- Verified that change reasons are exposed in forward-income results.
- Verified the existing forward-income functionality remained intact.
- **177 total automated tests passed across the complete test suite at sprint completion.**

Sprint 19M complete. RIMS can now automatically identify meaningful changes in forward-income positions while keeping the user-facing model simple and understandable.

---

## Sprint 19N — Forward Income Portfolio Report

**Objective:**

Create a simple portfolio-level forward-income report that combines current holdings, explicit forward-income assumptions, and automatically detected changes into one user-facing view.

**Files added:**

- `src/forward_income_report.py`
- `tests/test_forward_income_report.py`
- `tests/test_forward_income_report_integration.py`

**Implementation:**

- Created a user-facing `ForwardIncomeReport` data structure.
- Included current holdings, shares, market value, and Forward Annual Income.
- Included each holding's percentage of total forward annual income.
- Included automatically detected change reasons.
- Included total portfolio market value.
- Included total Forward Annual Income.
- Included counts of holdings with and without forward-income coverage.
- Included portfolio income concentration.
- Identified the holding producing the largest amount of Forward Annual Income.
- Used the existing `ForwardIncomeManager` to combine stored assumptions, current positions, change detection, and baseline management.
- Preserved the distinction between historical income and explicit forward-income assumptions.
- Did not annualize historical income.
- Did not substitute current yield for forward income.
- Did not introduce dividend-growth projections or other unsupported income projections.
- Preserved the RIMS principle that the user should see a simple income-focused result while complexity remains inside the software.
- Designed the report to show a closed position once with **Position Closed** and then remove it from subsequent reports.

**Testing:**

- Added automated tests for report creation and validation.
- Verified holding-level forward-income information.
- Verified portfolio-level totals.
- Verified largest-income-holding identification.
- Verified income concentration.
- Verified holdings without forward-income assumptions.
- Verified position-change detection is exposed in the report.
- Verified dividend-change detection is exposed in the report.
- Verified closed-position reporting behavior.
- Verified that report generation does not mutate the portfolio.
- Verified safe behavior when no forward-income assumptions exist.
- Added integration testing using the actual Schwab portfolio import.
- Verified the report correctly calculates position income as shares multiplied by expected annual income per share.
- **189 total automated tests passed across the complete test suite at sprint completion.**

Sprint 19N complete. RIMS can now produce a single portfolio-level view of expected annual income and clearly identify what changed in the current forward-income positions.

---

## Sprint 19O — Forward Income Review

**Objective:**

Create a concise portfolio review that identifies forward-income items requiring the user's attention, without making investment recommendations.

**Files added:**

- `src/forward_income_review.py`
- `tests/test_forward_income_review.py`
- `tests/test_forward_income_review_integration.py`

**Implementation:**

- Created a user-facing `ForwardIncomeReview` result.
- Created `ForwardIncomeReviewItem` for individual items requiring attention.
- Identified new positions.
- Identified position changes.
- Identified dividend changes.
- Identified combined position and dividend changes.
- Identified closed positions.
- Identified holdings with missing Forward Annual Income.
- Excluded holdings with no change from the review.
- Used the existing Sprint 19N `ForwardIncomeReport` as the source for review information.
- Did not perform another forward-income calculation.
- Did not create another portfolio baseline.
- Did not calculate yield.
- Did not annualize historical income.
- Did not make investment recommendations.
- Preserved the RIMS principle that complexity belongs in the software, not with the user.

**Testing:**

- Added 11 automated unit tests.
- Added 1 integration test.
- Verified all review categories.
- Verified unchanged holdings are excluded.
- Verified missing Forward Annual Income is identified.
- Verified shares and Forward Annual Income are preserved.
- Verified the review does not modify the underlying report.
- Verified integration with the Sprint 19N report structure.
- **201 total automated tests passed across the complete RIMS test suite at sprint completion.**

Sprint 19O complete. RIMS can now produce a concise review showing which forward-income holdings require the user's attention without making investment decisions for the user.

---

---

## Sprint 19P — RIMS Gap Assessment

**Status:** Complete

**Objective:**

Conduct a formal look-back assessment of the RIMS project following completion of Sprint 19O.

The assessment reviewed the original RIMS objectives, evaluated the capabilities completed through Sprint 19O, identified significant gaps, and established the architectural direction for the next phase of development.

**Files added:**

- `docs/Sprint19P_Gap_Assessment.md`

**Completed:**

- Reviewed the original RIMS product vision.
- Reviewed the original RIMS success criteria.
- Assessed the current portfolio, historical, transaction, income, forward-income, reporting, and review capabilities.
- Confirmed that the analytical foundation is sufficiently developed to begin application-layer development.
- Identified the RIMS Application / User Interface as the major remaining gap.
- Defined the required periodic data-import and analysis workflow.
- Defined the minimum Dashboard requirements.
- Established that the Dashboard must consume existing RIMS business logic rather than duplicate financial calculations.
- Identified capabilities that should remain deferred until the core application is operational.
- Established Sprint 20 as the beginning of the RIMS application phase.
- Reinforced the guiding principle:

**Complexity belongs in the software, not with the user.**

**Testing / Verification:**

- Gap assessment completed.
- Original project objectives reviewed.
- Current capabilities assessed.
- Major application-layer gap identified and documented.
- Sprint 20 direction established.
- No production financial logic changed.

**Result:**

Sprint 19P complete. RIMS has reached the point where development should transition from primarily adding analytical engines to integrating the existing capabilities into a practical user-facing application.

---

## Sprint 20 — RIMS Application Foundation

**Status:** Complete

**Objective:**

Establish the initial RIMS user-facing application framework and Dashboard shell while preserving the separation between the user interface, application workflow, and financial business logic.

**Files added:**

- `app/__init__.py`
- `app/app_config.py`
- `app/main.py`
- `app/pages/dashboard.py`
- `app/services/__init__.py`
- `tests/test_app_foundation.py`

**Files modified:**

- `requirements.txt`

**Implementation:**

- Added the RIMS Streamlit application framework.
- Added the main application entry point.
- Added application configuration.
- Added the initial Dashboard page.
- Added the application services package.
- Added Streamlit as a bounded runtime dependency.
- Established the foundation for application-level navigation.
- Kept financial calculations outside the Streamlit presentation layer.
- Established the local-browser application model for RIMS.

**Testing:**

- Added 8 automated application-foundation tests.
- Verified application identity and configuration.
- Verified project and application paths.
- Verified required application files.
- Verified application entry-point functions.
- Verified Dashboard availability.
- **219 total automated tests passed across the complete RIMS test suite at sprint completion.**
- Verified the application successfully launched through Streamlit.

**Acceptance:**

- RIMS application framework operational.
- Dashboard shell operational.
- Existing RIMS financial functionality remains separated from the presentation layer.
- Application successfully runs locally in a browser.

Sprint 20 complete.

---

## Sprint 21 — Schwab Import Validation Workflow

**Status:** Complete

**Objective:**

Allow the user to select Schwab position and transaction files, validate them, and prepare them for import into RIMS without modifying persistent financial data until validation succeeds.

**Files added:**

- `app/pages/import_data.py`
- `app/services/import_service.py`
- `tests/test_import_data.py`
- `tests/test_import_service.py`

**Files modified:**

- `app/main.py`

**Implementation:**

- Added the RIMS Import Data application page.
- Added separate Schwab Positions and Schwab Transactions validation workflows.
- Added an application-layer `ImportService` that wraps the existing Schwab importers.
- Added structured positions validation results.
- Added structured transaction validation results.
- Added positions reconciliation reporting.
- Added transaction counts, income counts, recurring income, and transaction date-range reporting.
- Added transaction account entry because Schwab transaction exports do not contain the RIMS account name.
- Added temporary handling of uploaded files without persisting financial data.
- Added validation error handling for missing files and invalid Schwab files.
- Added native Streamlit navigation for Dashboard and Import Data.
- Preserved the separation between the Streamlit UI, application services, and existing financial/import business logic.
- No persistent portfolio, transaction, snapshot, or forward-income data is modified by validation.

**Testing:**

- Added 10 automated Import Service tests.
- Added 6 automated Import Data page tests.
- Verified valid positions-file validation.
- Verified positions reconciliation.
- Verified invalid/unrecognized positions files.
- Verified valid transaction-file validation.
- Verified missing transaction account handling.
- Verified invalid/unrecognized transaction files.
- Verified validation results are displayed correctly.
- **225 total automated tests passed across the complete RIMS test suite at sprint completion.**

**Real Schwab-file validation:**

Using the user's actual Schwab exports:

- Positions file successfully validated.
- **44 holdings** recognized.
- Market value difference: **$0.00**.
- Cost basis difference: **$0.00**.
- Schwab positions reconciliation passed.

Using an actual Contributory account transaction export:

- **22 transactions** recognized.
- **21 income transactions** recognized.
- Recurring income: **$2,855.75**.
- Transaction date range: **07/01/2026–07/31/2026**.

An incorrectly selected positions file was also rejected by the transaction validator, confirming that the validation workflow detects an inappropriate file type before any persistent import occurs.

**Acceptance:**

- Schwab positions files can be selected and validated.
- Schwab transaction files can be selected and validated.
- Validation results are presented clearly to the user.
- Existing Schwab importers remain the source of parsing and classification logic.
- Validation does not modify persistent financial data.
- Real Schwab files successfully passed the appropriate validation workflows.

Sprint 21 complete.

---

## Upcoming Development

The next development phase should build on the validated application workflow by adding the controlled **import/update process** that follows successful validation.

The next sprint should **not** automatically overwrite the current portfolio or historical records. It should establish the controlled transition:

```text
Select File
    ↓
Validate
    ↓
Review Validation Results
    ↓
Import / Update RIMS
    ↓
Preserve Historical Data
    ↓
Update Current Portfolio
