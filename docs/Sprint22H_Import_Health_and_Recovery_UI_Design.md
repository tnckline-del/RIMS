# Sprint 22H — Import Health and Recovery UI Design

## 1. Purpose

Sprint 22H completes the user-facing portion of the controlled import
reconciliation workflow established in Sprint 22G.

The goal is to expose the persisted import lifecycle to the user through the
Import Data page.

The UI must allow the user to:

1. see the current health of persisted import operations,
2. review the history of individual import operations,
3. identify imports requiring reconciliation,
4. recover failed reconciliation without re-importing the source CSV, and
5. see whether a newly imported positions or transactions file has completed
   post-import reconciliation.

Sprint 22H does not replace the durable ImportOperation lifecycle established
in Sprint 22G.

---

## 2. Core Principle

The Import Data page is a presentation and workflow layer over the existing
persisted import lifecycle.

The backend remains responsible for:

- controlled import,
- persistence of authoritative source data,
- post-import processing,
- reconciliation,
- failure tracking, and
- recovery.

The UI exposes that lifecycle without creating a second source of truth.

The workflow is:

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
               Import History
                      |
                      v
                   Recover
                      |
                      v
                 RECONCILED

---

## 3. Relationship to Sprint 22G

Sprint 22G established the durable reconciliation and recovery lifecycle.

Sprint 22H builds the application-level workflow around that lifecycle.

Sprint 22G provides:

- ImportReconciliationService,
- RECONCILED status,
- RECONCILIATION_FAILED status,
- recovery using authoritative persisted data,
- independent lifecycle state for each import operation, and
- import health derived from persisted ImportOperation records.

Sprint 22H provides:

- application-service wiring for the import workflow,
- reconciliation integration into positions imports,
- reconciliation integration into transaction imports,
- Import Health display,
- Import History display,
- recovery controls in Import History,
- user-facing success and failure messages, and
- recovery retry behavior through the UI.

Sprint 22H does not introduce a new financial-processing layer.

---

## 4. Application Service Wiring

The Import Data page constructs the application services required for the
controlled import workflow.

The application services include:

- ControlledPositionsImportService,
- ControlledTransactionImportService,
- PostImportProcessingCoordinator,
- ImportReconciliationService, and
- ImportHealthService.

The services share the existing authoritative storage components:

- ImportOperationStore,
- SnapshotStore, and
- TransactionRepository.

The PostImportProcessingCoordinator receives the configured Forward Income
storage path.

The ImportReconciliationService receives the existing import operation store,
snapshot store, transaction repository, and post-import processing coordinator.

The ImportHealthService receives the existing ImportOperationStore.

No second lifecycle store is introduced.

---

## 5. Positions Import Workflow

The positions workflow remains responsible for validating and importing the
Schwab positions file.

After successful controlled import:

    Positions CSV
        |
        v
    controlled positions import
        |
        v
      IMPORTED
        |
        v
    ImportReconciliationService
       /           \
    success        failure
      |               |
      v               v
 RECONCILED   RECONCILIATION_FAILED

When reconciliation succeeds, the UI reports:

    Positions import completed and reconciled.

When reconciliation fails, the UI reports that the import completed but
post-import reconciliation failed and directs the user to Import History for
recovery.

A reconciliation failure does not invalidate the successfully imported
positions data.

---

## 6. Transaction Import Workflow

The transaction workflow remains responsible for validating and importing the
Schwab transaction file.

After successful controlled import:

    Transactions CSV
        |
        v
    controlled transaction import
        |
        v
      IMPORTED
        |
        v
    ImportReconciliationService
       /           \
    success        failure
      |               |
      v               v
 RECONCILED   RECONCILIATION_FAILED

When reconciliation succeeds, the UI reports:

    Transaction import completed and reconciled.

When reconciliation fails, the UI reports that the import completed but
post-import reconciliation failed and directs the user to Import History for
recovery.

The imported transaction data remains persisted when post-import processing
fails.

---

## 7. Import Health

The Import Data page displays persisted import health.

Import Health is derived from ImportOperation records through the existing
ImportHealthService.

The UI displays:

- Total Imports,
- Reconciled, and
- Reconciliation Issues.

When no operations exist, the UI displays:

    No import operations recorded.

When one or more operations require reconciliation, the UI displays the
persisted health summary as a warning.

When all recorded operations are reconciled, the UI displays the persisted
health summary as a success message.

When operations exist but reconciliation is still pending, the UI displays the
persisted health summary as an informational message.

Import Health is factual lifecycle information.

No financial-health score or investment assessment is introduced.

---

## 8. Import History

The Import Data page displays persisted ImportOperation records in reverse
chronological order.

Each operation displays:

- source file,
- file type,
- lifecycle status,
- account when available, and
- import timestamp.

The UI presents lifecycle-specific status information.

### RECONCILED

The operation is displayed as:

    Reconciled

### IMPORTED

The operation is displayed as:

    Imported — pending reconciliation

### RECONCILIATION_FAILED

The operation is displayed as requiring reconciliation and provides a:

    Recover

control.

### IMPORT_FAILED

The operation is displayed as:

    Import failed

### VALIDATION_FAILED

The operation is displayed as:

    Validation failed

The persisted ImportOperation remains the authoritative lifecycle record.

---

## 9. Recovery Workflow

Recovery is initiated from Import History for an operation whose status is
RECONCILIATION_FAILED.

The UI invokes ImportReconciliationService.recover() using the persisted
ImportOperation identifier.

The source CSV is not re-imported by the UI recovery workflow.

The recovery process therefore continues to follow the Sprint 22G authority
rules.

When recovery succeeds:

1. the UI reports that recovery completed,
2. the operation is reconciled by the reconciliation service, and
3. the Import Data page is rerun so the displayed health and history reflect
   the new lifecycle state.

When recovery raises an exception:

1. the UI reports the recovery failure, and
2. the existing operation remains available for another recovery attempt.

When recovery returns without reconciliation being completed, the UI reports
that recovery did not complete successfully and directs the user to review
Import History and try again.

---

## 10. Failure Isolation

Sprint 22H preserves the distinction between import failure and
post-import reconciliation failure.

An import failure remains an import failure.

A successfully persisted import whose downstream processing fails remains a
successful import with:

    RECONCILIATION_FAILED

The UI must not represent such an operation as IMPORT_FAILED.

The imported source data therefore remains available for recovery.

A reconciliation failure also does not prevent subsequent independent import
operations.

---

## 11. Independent Import Operations

The UI may display multiple operations together in Import History, but each
operation retains its independent lifecycle.

For example:

    Positions CSV
        -> RECONCILED

    Transaction CSV #1
        -> RECONCILED

    Transaction CSV #2
        -> RECONCILIATION_FAILED

    Transaction CSV #3
        -> RECONCILED

Import History must retain the unresolved state of Transaction CSV #2 while
still displaying the successful state of the other operations.

Import Health must not report that all imports are reconciled while an
operation remains in RECONCILIATION_FAILED.

---

## 12. Authoritative Data and Processing

Sprint 22H does not change the authoritative data rules established by
previous sprints.

Positions remain authoritative through the existing persisted Snapshot rules.

Transactions remain authoritative through the existing TransactionRepository.

Post-import processing remains the responsibility of
PostImportProcessingCoordinator.

ImportReconciliationService remains responsible for lifecycle reconciliation
and recovery orchestration.

The Import Data page does not perform financial calculations itself.

---

## 13. UI State Preservation

When a controlled import succeeds but reconciliation fails, the UI retains the
successful import result and imported-file identity.

The validation state is cleared after the controlled import has completed.

The reconciliation failure is represented independently through the persisted
ImportOperation lifecycle.

This ensures that a downstream processing failure does not make the UI behave
as though the source import itself failed.

---

## 14. Testing Requirements

Sprint 22H tests must cover:

### Application wiring

- Application services are constructed with the expected shared dependencies.
- PostImportProcessingCoordinator receives the Forward Income storage path.
- ImportReconciliationService receives the authoritative storage components.
- ImportHealthService uses the existing ImportOperationStore.

### Import workflows

- Successful positions imports invoke reconciliation.
- Successful transaction imports invoke reconciliation.
- Positions reconciliation failures are displayed to the user.
- Transaction reconciliation failures are displayed to the user.
- Successfully imported data remains represented after reconciliation failure.

### Import Health

- No operations display an informational message.
- Reconciliation failures produce a warning.
- All reconciled operations produce a success message.
- Pending reconciliation produces an informational message.

### Import History

- Reconciled operations display as reconciled.
- Failed reconciliation displays a recovery action.
- Empty history displays an informational message.
- Import and validation failures remain distinguishable.

### Recovery

- Successful recovery displays success and reruns the page.
- Recovery exceptions are displayed as errors.
- An unresolved recovery result is displayed as an error.

### Regression

All existing tests must continue to pass.

---

## 15. Out of Scope

Sprint 22H does not introduce:

- new financial calculations,
- new income-analysis algorithms,
- portfolio scoring,
- investment recommendations,
- automatic source-file downloading,
- automatic retry scheduling,
- a second ImportOperation store,
- a second transaction database,
- a second portfolio source of truth,
- a combined lifecycle record for multiple files, or
- changes to the underlying authoritative data rules.

---

## 16. 22H Completion Criteria

Sprint 22H is complete when:

1. The Import Data page constructs the required application services.
2. Positions imports invoke post-import reconciliation.
3. Transaction imports invoke post-import reconciliation.
4. Reconciliation failures remain distinguishable from import failures.
5. Import Health reflects persisted ImportOperation lifecycle state.
6. Import History displays persisted import operations.
7. Failed reconciliation operations expose a recovery action.
8. Successful recovery refreshes the displayed lifecycle state.
9. Recovery failures remain visible and retryable.
10. Successfully imported source data remains represented after reconciliation
    failure.
11. Independent import operations remain independent.
12. Existing Sprint 22G reconciliation and recovery behavior remains intact.
13. Existing tests continue to pass.
14. New Sprint 22H application and UI tests pass.
15. Production code contains no placeholders or TODOs.

---

## 17. Architectural Principle

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
    Expose lifecycle state to the user.
        |
        v
    Recover processing independently when necessary.

Sprint 22H makes the durable import lifecycle visible and actionable without
creating a second source of truth.

The backend lifecycle remains authoritative.

The Import Data page provides the user with factual visibility into import
health, import history, reconciliation failures, and recovery.
