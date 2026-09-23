# Sprint 22E — Import UI Design

## 1. Purpose

Sprint 22E establishes the Streamlit user interface for the controlled Schwab import workflow.

The purpose of this sprint is to provide a clear and safe user workflow for:

- Selecting Schwab positions files.
- Selecting Schwab transaction files.
- Providing the RIMS account for transaction imports.
- Validating selected files.
- Reviewing validation results.
- Explicitly confirming an import.
- Executing the appropriate controlled import service.
- Displaying the actual import results.

The UI must not independently perform financial calculations or directly modify persistent RIMS data.

The architecture is:

    Schwab file
          ↓
    Streamlit Import UI
          ↓
    ImportService validation
          ↓
    Validation result
          ↓
    Explicit user import action
          ↓
    Controlled Import Service
          ↓
    Persistent RIMS data


## 2. Responsibilities

### Import Data UI

The Import Data page is responsible for:

- Presenting file-selection controls.
- Presenting the transaction account input.
- Calling the existing validation service.
- Displaying validation results.
- Retaining validated source-file data across Streamlit reruns.
- Requiring an explicit import action after validation.
- Calling the appropriate controlled import service.
- Displaying the actual import result.
- Displaying errors without suppressing them.
- Keeping positions and transactions independently importable.

The UI does not:

- Parse Schwab CSV files.
- Classify transactions.
- Calculate historical income.
- Calculate forward income.
- Calculate portfolio values.
- Perform transaction duplicate detection.
- Perform source-file duplicate detection.
- Persist transactions directly.
- Persist snapshots directly.
- Modify import-operation records directly.

Those responsibilities remain in the existing RIMS services.


## 3. Independent Import Workflows

Positions and transactions are intentionally independent workflows.

### Positions

    Select positions file
          ↓
    Validate
          ↓
    Review validation
          ↓
    IMPORT POSITIONS INTO RIMS
          ↓
    ControlledPositionsImportService
          ↓
    Snapshot persistence


### Transactions

    Select transaction file
          ↓
    Enter RIMS account
          ↓
    Validate
          ↓
    Review validation
          ↓
    IMPORT TRANSACTIONS INTO RIMS
          ↓
    ControlledTransactionImportService
          ↓
    Transaction persistence

An error or failure in one workflow must not prevent the other workflow from being used.


## 4. Validation Boundary

Validation must occur before persistent import.

A successful validation result is required before an import button is presented.

The UI must not:

- Import an invalid validation result.
- Bypass `ImportService`.
- Recalculate validation results independently.

The existing validation service remains authoritative for Schwab file validation.


## 5. Positions Validation Results

After successful positions validation, the UI displays the information already supplied by `PositionsValidationResult`, including:

- Holdings count.
- Market-value difference.
- Cost-basis difference.
- Reconciliation status.
- Schwab reporting date when available through the validation/import result.

A failed validation displays the validation error and does not present an import action.


## 6. Transaction Validation Results

After successful transaction validation, the UI displays:

- Transaction count.
- Income transaction count.
- Recurring-income amount.
- Transaction start date.
- Transaction end date.

These values describe the validated source file.

They are not presented as the amount newly added to RIMS.

The actual number of transactions added is reported only after controlled import.


## 7. Explicit Import Action

Validation and import are separate actions.

The user must explicitly select:

- `IMPORT POSITIONS INTO RIMS`

or:

- `IMPORT TRANSACTIONS INTO RIMS`

after reviewing the validation results.

Validation alone must never change persistent RIMS data.

The UI should clearly indicate that the import action changes persistent RIMS data.


## 8. Streamlit Session State

Streamlit reruns the page when controls are activated.

The validated result therefore cannot depend on a temporary file that is deleted immediately after validation.

The UI must retain sufficient validated state to perform the later import.

For each workflow, session state must retain:

- Selected filename.
- Uploaded file contents.
- Validation result.

The original uploaded bytes are retained so the physical source file can be recreated for the controlled import service.

Temporary files created for validation or import must be removed after use.


## 9. Source File Handling

Uploaded files are temporarily written to disk because the existing validation and controlled import services operate on filesystem paths.

The UI must:

1. Receive the uploaded file.
2. Preserve the uploaded bytes in session state.
3. Write a temporary copy when validation is requested.
4. Run validation.
5. Remove the validation temporary file.
6. Recreate a temporary source file when import is requested.
7. Run the appropriate controlled import service.
8. Remove the import temporary file.

The UI must not move or copy the source file into the permanent RIMS data directories.

Persistent source-file provenance is handled by the controlled import services.


## 10. Positions Import Result

After successful positions import, the UI should report:

- Snapshot date.
- Holdings imported.
- Whether the current portfolio advanced.

The result must distinguish between:

### Current portfolio advanced

The imported positions snapshot is newer than the previously current snapshot.

### Historical snapshot only

The imported reporting date is not newer than the current positions snapshot.

In either case, the historical snapshot has been persisted by the controlled positions import service.


## 11. Transaction Import Result

After successful transaction import, the UI should report:

- Transactions received.
- Transactions added.
- Duplicates skipped.
- Income transactions added.
- Recurring-income transactions added.

These values come from `ControlledTransactionImportResult`.

The UI must not substitute the validation result's recurring-income amount for the actual import result.


## 12. Duplicate Handling

Duplicate detection remains entirely within the controlled import layer.

The UI does not attempt to determine whether a file or transaction is a duplicate.

If the controlled transaction importer reports:

- `transactions_added = 0`
- `duplicates_skipped > 0`

the UI reports that the transaction file was processed successfully but contained no previously unseen transactions.

A duplicate source file rejected by the controlled importer is displayed as an import error.


## 13. Persistent Store Wiring

The UI obtains persistent storage paths from `app.app_config`.

The authoritative paths are:

- `SNAPSHOT_DIR`
- `TRANSACTION_DIR`
- `IMPORT_OPERATION_DIR`

The UI must not hard-code production data paths.

The controlled services are constructed using:

    ImportOperationStore(IMPORT_OPERATION_DIR)

    SnapshotStore(SNAPSHOT_DIR)

    TransactionRepository.from_path(TRANSACTION_DIR)


The resulting services are:

    ControlledPositionsImportService(
        import_operation_store,
        snapshot_store,
    )

    ControlledTransactionImportService(
        import_operation_store,
        transaction_repository,
    )


## 14. Error Handling

Validation and import errors must be displayed to the user.

The UI must not silently suppress exceptions from the controlled import services.

A failed controlled import must leave the controlled service responsible for recording its appropriate import-operation failure status.

The UI displays the failure and allows the user to correct the problem and continue using the application.

Recovery and transactional rollback behavior remain the responsibility of later Sprint 22 failure/recovery work.


## 15. Session-State Isolation

Positions and transaction workflows must maintain separate session-state keys.

A successful positions validation must not overwrite a transaction validation result.

A successful transaction validation must not overwrite a positions validation result.

Importing one workflow must clear only the relevant validated state after successful completion.


## 16. Revalidation

Changing the selected source file or transaction account invalidates the previously validated state for that workflow.

The UI must not allow a validation result for one source file to be imported using a different source file.

The controlled services provide an additional filename/provenance boundary, but the UI should maintain correct state as well.


## 17. User Workflow

The intended user workflow is:

### Positions

1. Select a Schwab positions CSV.
2. Select `Validate Positions File`.
3. Review validation results.
4. If validation succeeds, select `IMPORT POSITIONS INTO RIMS`.
5. Review the import confirmation.
6. Continue using RIMS.

### Transactions

1. Select a Schwab transactions CSV.
2. Enter the RIMS account.
3. Select `Validate Transactions File`.
4. Review validation results.
5. If validation succeeds, select `IMPORT TRANSACTIONS INTO RIMS`.
6. Review the import confirmation.
7. Continue using RIMS.


## 18. Architectural Boundary

Sprint 22E establishes the following application boundary:

    Streamlit UI
          ↓
    Validation Service
          ↓
    Controlled Import Service
          ↓
    Persistence

The UI is an orchestration and presentation layer.

It is not an alternative financial calculation or persistence layer.


## 19. Testing Requirements

Sprint 22E tests should verify:

### Configuration

- Production storage paths resolve correctly.
- Snapshot, transaction, and import-operation directories are distinct.

### UI validation workflow

- Positions validation can be initiated.
- Transaction validation can be initiated.
- Validation failures are displayed.
- Successful validation results are retained.

### UI import workflow

- Import controls appear only after successful validation.
- Positions import invokes the controlled positions importer.
- Transaction import invokes the controlled transaction importer.
- Import results are displayed.
- Validated state is cleared after successful import.
- Positions and transaction state remain independent.

### Safety

- A changed filename cannot reuse a previous validation result.
- A changed transaction account cannot reuse a previous validation result.
- Invalid validation results cannot reach the controlled import service.
- Temporary files are removed after validation/import processing.
- Controlled import exceptions are surfaced to the user.

The UI tests should use test doubles or isolated temporary stores rather than modifying the user's production RIMS data.


## 20. Scope Boundary

Sprint 22E does not implement:

- Post-import portfolio reconciliation.
- Post-import income-history rebuilding.
- Forward-income updates.
- Transactional rollback.
- Import recovery workflows.
- Advisor workflows.
- Additional financial analysis.

Those remain later Sprint 22 responsibilities.


## 21. Completion Criteria

Sprint 22E is complete when:

- The Import Data page supports positions validation and import.
- The Import Data page supports transaction validation and import.
- Validation must precede import.
- Import requires explicit user action.
- Persistent paths come from application configuration.
- Controlled import services perform all persistent changes.
- Actual import results are displayed.
- Session state safely survives Streamlit reruns.
- Temporary uploaded files are cleaned up.
- UI tests cover the major validation and import paths.
- The full RIMS test suite passes.
