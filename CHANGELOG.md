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

## Upcoming Development


**Planned objective:**  
Establish the RIMS historical snapshot capability so portfolio values, holdings, income, and other important metrics can be preserved at specific points in time.

Planned capabilities include:

- Point-in-time portfolio snapshots.
- Preservation of historical holdings.
- Historical market value.
- Historical cost basis.
- Historical forward annual dividend income.
- Historical portfolio yield.
- Snapshot dates.
- Comparison of current and historical portfolio states.

The detailed Sprint 12 scope will be defined before implementation begins.
