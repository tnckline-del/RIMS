# Sprint 22G — Import Reconciliation and Recovery Design

## 1. Purpose

Sprint 22G completes the controlled import workflow by adding durable
post-import reconciliation, failure tracking, and recovery.

The goal is to ensure that every successfully imported source file has an
independently trackable processing lifecycle.

The system must distinguish:

1. successful persistence of source data,
2. successful post-import financial processing, and
3. unresolved post-import processing failures.

A reconciliation failure must not invalidate successfully imported source data
and must not prevent subsequent independent imports.

---

## 2. Core Principle

Each uploaded CSV file is an independent ImportOperation.

The lifecycle is:

    controlled import
          |
          v
       IMPORTED
          |
          v
    post-import processing
       /           \
    success        failure
      |               |
      v               v
 RECONCILED   RECONCILIATION_FAILED
                      |
                      v
                   recovery
                      |
                      v
                 RECONCILED

Import processing and reconciliation are therefore independently recoverable
for every source file.

---

## 3. Real-World Workflow

RIMS must support the following normal workflow:

    Positions CSV
        -> IMPORTED
        -> processed
        -> RECONCILED

    Transaction CSV #1
        -> IMPORTED
        -> processed
        -> RECONCILED

    Transaction CSV #2
        -> IMPORTED
        -> processing fails
        -> RECONCILIATION_FAILED

    Transaction CSV #3
        -> IMPORTED
        -> processed
        -> RECONCILED

Transaction CSV #2 remains an unresolved processing exception, but its failure
does not prevent Transaction CSV #3 from being imported and processed.

---

## 4. Existing Import Status Model

The existing ImportStatus values remain the lifecycle vocabulary:

- VALIDATED
- CONFIRMED
- STAGED
- IMPORTED
- RECONCILED
- VALIDATION_FAILED
- IMPORT_FAILED
- RECONCILIATION_FAILED

Sprint 22G does not introduce a separate processing-status database.

The existing ImportOperation remains the durable lifecycle record.

---

## 5. Status Semantics

### IMPORTED

The source file has been successfully validated and its data has been
persisted into the authoritative RIMS dataset.

For positions:

- the positions snapshot has been persisted.

For transactions:

- the unique transactions have been persisted to the transaction repository.

IMPORTED does not mean that all downstream analysis has completed.

### RECONCILED

The post-import processing required for that ImportOperation has completed
successfully using authoritative persisted RIMS data.

### RECONCILIATION_FAILED

The source data was successfully imported, but required post-import processing
failed.

The imported data remains valid and must not be removed or rolled back merely
because downstream processing failed.

The operation is eligible for recovery.

---

## 6. Independent Import Operations

Positions and transactions are not represented as one combined ImportOperation.

A positions CSV creates one positions ImportOperation.

Each transaction CSV creates its own transaction ImportOperation.

For example:

    Positions-2026-09-23.csv
        -> positions operation

    Transactions-1.csv
        -> transaction operation

    Transactions-2.csv
        -> transaction operation

    Transactions-3.csv
        -> transaction operation

Each operation has its own lifecycle and reconciliation status.

---

## 7. Authoritative Data Sources

The existing Sprint 22F authority rules remain unchanged.

### Positions

The authoritative current portfolio is the latest successful persisted
positions Snapshot according to the existing controlled positions import rules.

### Transactions

The authoritative transaction dataset is the persisted TransactionRepository
dataset.

Recovery must process authoritative persisted data rather than re-reading and
re-importing the original CSV.

---

## 8. Post-Import Processing

The existing PostImportProcessingCoordinator remains an orchestration layer.

It continues to:

- load authoritative persisted positions,
- load authoritative persisted transactions,
- run Current Income,
- run Forward Income,
- run Historical Income,
- return a structured processing result.

Sprint 22G does not move financial calculations into the reconciliation layer.

The existing 22F processing rules remain:

### Positions import

Runs:

- Current Income
- Forward Income

### Transaction import with new transactions

Runs:

- Historical Income
- Current Income

### Transaction import containing only duplicates

Does not trigger transaction-driven analysis.

---

## 9. Reconciliation Responsibility

A new lifecycle/reconciliation service is responsible for:

1. accepting a successfully imported operation,
2. invoking the applicable post-import processing,
3. marking the operation RECONCILED after successful processing,
4. marking the operation RECONCILIATION_FAILED when processing fails,
5. preserving the imported operation and data after failure,
6. supporting later recovery.

The reconciliation layer does not perform financial calculations itself.

---

## 10. Recovery

Recovery operates against the persisted authoritative datasets.

Recovery must not:

- re-import the original CSV,
- create duplicate transactions,
- create a second portfolio source of truth,
- delete successfully imported data.

Recovery of a failed transaction import may occur after later transaction
imports have already succeeded.

The recovery process therefore operates against the current authoritative
transaction repository rather than attempting to reconstruct the historical
repository state from the failed CSV.

---

## 11. Subsequent Imports After Failure

A RECONCILIATION_FAILED operation does not block subsequent imports.

Example:

    Transaction #2
        RECONCILIATION_FAILED

    Transaction #3
        IMPORTED
        -> processed
        -> RECONCILED

RIMS must retain the unresolved failure for Transaction #2.

The system must never report that all imports are reconciled while one or more
operations remain in RECONCILIATION_FAILED or otherwise require recovery.

---

## 12. Import Health

Sprint 22G should expose factual lifecycle state rather than a subjective
score.

Examples:

    All imports reconciled

or:

    1 import requires reconciliation

or:

    2 imports require reconciliation

The state is derived from persisted ImportOperation records.

No financial-health score is introduced by Sprint 22G.

---

## 13. Failure Isolation

A post-import processing failure is distinct from an import failure.

If source data has been successfully persisted:

    IMPORTED
        |
        v
    processing failure
        |
        v
    RECONCILIATION_FAILED

It must not become:

    IMPORT_FAILED

The distinction is important because the source data remains valid and
recoverable.

---

## 14. Lifecycle Persistence

ImportOperation remains the durable lifecycle record.

Existing ImportOperationStore behavior is retained:

- save protects existing records by default,
- explicit overwrite is required to replace an operation,
- load retrieves the current lifecycle state,
- list_operations returns persisted operations,
- find_by_file_hash remains available for source-file identity checks.

Sprint 22G may add narrowly scoped lifecycle operations to the store if
required, but must not create a second source of truth for ImportOperation
status.

---

## 15. Idempotency

Recovery must be safe to retry.

A successfully reconciled operation must not be processed again unnecessarily
when recovery is requested.

A failed operation may be processed again.

Transaction persistence remains protected by the existing transaction
fingerprint mechanism.

Recovery must not create duplicate transaction records.

---

## 16. Combined UI Workflow

The user may select or import multiple files during an application session,
but the backend lifecycle remains independent per file.

The UI may present a convenient multi-file workflow, but each file receives
its own ImportOperation and reconciliation state.

Sprint 22G does not require a combined import-status record.

---

## 17. Processing Failure and Recovery Example

Initial state:

    Positions       RECONCILED
    Transaction #1  RECONCILED
    Transaction #2  RECONCILIATION_FAILED
    Transaction #3  RECONCILED

The transaction repository contains the successfully imported transactions
from all three transaction files.

Recovery of Transaction #2:

    load Transaction #2 operation
    verify it requires reconciliation
    load authoritative transaction repository
    load authoritative current portfolio when required
    run applicable analysis
    success -> RECONCILED
    failure -> RECONCILIATION_FAILED

The source CSV is not re-imported.

---

## 18. Testing Requirements

Sprint 22G tests must cover:

### Lifecycle

- IMPORTED can become RECONCILED after successful processing.
- IMPORTED can become RECONCILIATION_FAILED after processing failure.
- RECONCILIATION_FAILED can be recovered to RECONCILED.
- A RECONCILED operation remains complete.

### Independent operations

- Positions and transactions have independent lifecycle state.
- One failed transaction reconciliation does not alter a reconciled positions
  operation.
- One failed transaction reconciliation does not prevent a later transaction
  import.

### Recovery

- Recovery uses authoritative persisted data.
- Recovery does not re-import the source CSV.
- Recovery does not duplicate transactions.
- Recovery can succeed after later transaction imports have occurred.
- Repeated recovery attempts are safe.

### Failure isolation

- Import failure remains IMPORT_FAILED.
- Post-import processing failure becomes RECONCILIATION_FAILED.
- Successfully imported data remains persisted after processing failure.

### Regression

All existing Sprint 22B through 22F tests must continue to pass.

---

## 19. Out of Scope

Sprint 22G does not introduce:

- new financial calculations,
- new income-analysis algorithms,
- Dashboard financial presentation,
- portfolio scoring,
- investment recommendations,
- automated source-file downloading,
- automatic retry scheduling,
- a second transaction database,
- a second portfolio source of truth,
- a combined ImportOperation for multiple files.

---

## 20. 22G Completion Criteria

Sprint 22G is complete when:

1. Each imported CSV has an independently persisted lifecycle.
2. Successful processing results in RECONCILED.
3. Processing failure results in RECONCILIATION_FAILED.
4. Later imports are permitted after a reconciliation failure.
5. Failed reconciliation can be recovered without re-importing the source CSV.
6. Recovery uses authoritative persisted RIMS data.
7. Transaction idempotency remains intact.
8. Import failures remain distinguishable from reconciliation failures.
9. Import health can identify unresolved reconciliation failures.
10. Existing 22F processing behavior remains unchanged.
11. All existing tests pass.
12. New 22G lifecycle and recovery tests pass.
13. Production code contains no placeholders or TODOs.

---

## 21. Architectural Principle

RIMS follows this sequence:

    Import safely.
        |
        v
    Persist authoritative data.
        |
        v
    Process from authoritative persisted data.
        |
        v
    Reconcile the ImportOperation.
        |
        v
    Recover processing independently when necessary.

The source data and its lifecycle state must remain durable even when
downstream financial analysis temporarily fails.
