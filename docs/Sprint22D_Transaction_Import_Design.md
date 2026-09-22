# Sprint 22D — Controlled Transaction Import Design

## 1. Purpose

Sprint 22D establishes the controlled transaction-import layer for RIMS.

The purpose of this sprint is to safely incorporate validated Schwab transaction data into the persistent RIMS transaction history without creating duplicate transactions or allowing the import process to perform financial analysis.

The controlled transaction import process sits between transaction validation and persistent transaction storage.

The architecture is:

    Schwab transaction file
            ↓
    ImportService validation
            ↓
    TransactionsValidationResult
            ↓
    ControlledTransactionImportService
            ↓
    TransactionRepository
            ↓
    Persistent transaction datasets

Import-operation tracking is maintained throughout the process.

---

## 2. Responsibilities

### ControlledTransactionImportService

The controlled import service is responsible for:

- Accepting a successfully validated transaction result.
- Verifying the physical source file.
- Calculating the source-file SHA-256 hash.
- Preventing the same source file from being imported twice.
- Creating the import operation.
- Passing validated transactions to TransactionRepository.
- Recording import success or failure.
- Reporting the transactions actually added.
- Reporting income and recurring-income counts for transactions actually added.

The service does not:

- Parse Schwab CSV files.
- Independently classify transactions.
- Calculate historical income.
- Calculate forward income.
- Modify portfolio values.
- Replace existing transaction history.

Those responsibilities remain in the appropriate existing RIMS services.

---

## 3. TransactionRepository Responsibilities

TransactionRepository is responsible for transaction persistence and transaction-level duplicate detection.

Sprint 22D adds:

- Deterministic transaction fingerprints.
- Existing transaction fingerprint retrieval.
- Controlled append behavior.
- Duplicate suppression within an incoming batch.
- Duplicate suppression against previously persisted transactions.
- Reporting of transactions actually added.

The repository does not know anything about Schwab CSV parsing or import workflow state.

---

## 4. Transaction Identity

A transaction fingerprint is a SHA-256 hash of a canonical JSON representation of the economic transaction.

The fingerprint includes:

- account
- transaction date
- action
- symbol
- description
- amount
- transaction type
- income type
- income character
- tax character
- quantity
- price
- fees and commissions

The fingerprint deliberately excludes:

- source file

The same transaction may legitimately appear in multiple overlapping Schwab exports. Source-file provenance therefore must not make an otherwise identical transaction appear to be a different economic transaction.

Canonical JSON uses sorted keys and deterministic separators before SHA-256 hashing.

---

## 5. Duplicate Handling

Duplicate detection occurs at two levels.

### Existing historical transactions

If a transaction fingerprint already exists in persistent transaction history, the transaction is skipped.

### Duplicate transactions within the incoming batch

If the same transaction appears more than once in the incoming batch, the first occurrence is retained and subsequent occurrences are skipped.

The result reports:

- transactions received
- transactions added
- duplicates skipped
- transactions actually added

---

## 6. All-Duplicate Imports

An import containing only duplicate transactions is considered successfully processed.

In this case:

- `transactions_added` is zero.
- `duplicates_skipped` equals the number of incoming transactions.
- No new TransactionDataset is created.
- The controlled import operation can still advance to `IMPORTED`.

This distinguishes transaction-level duplication from duplicate source-file processing.

---

## 7. Duplicate Source Files

The controlled transaction import service calculates the SHA-256 hash of the physical source file before changing persistent transaction data.

If that hash already exists in ImportOperationStore, the source file is rejected as previously imported.

This protection occurs before transaction persistence.

Source-file duplicate detection and transaction-level duplicate detection therefore serve different purposes:

- Source-file hash prevents processing the same physical export twice.
- Transaction fingerprint prevents overlapping exports from creating duplicate historical transactions.

---

## 8. Import Operation Lifecycle

A successful transaction import follows this lifecycle:

    VALIDATED
        ↓
    CONFIRMED
        ↓
    transaction append
        ↓
    IMPORTED

The controlled service creates the `ImportOperation` with:

- import ID
- source file
- file type
- file hash
- account
- reporting start date
- reporting end date
- import timestamp
- import status

The transaction import ID is deterministic from the source-file hash:

    transactions-{first 16 characters of SHA-256 hash}

---

## 9. Import Failure

If transaction persistence fails after the operation has been created:

- The operation is changed to `IMPORT_FAILED`.
- The original exception is re-raised.
- The failure is therefore visible to the caller.

The controlled import service does not silently suppress persistence failures.

Recovery and transactional rollback hardening are deferred to the later Sprint 22G failure/recovery work.

---

## 10. Income Reporting

The controlled transaction import service reports income classifications only for transactions actually added to RIMS.

It reports:

- income transactions added
- recurring-income transactions added

It does not calculate or persist historical income totals.

In particular, the validation result's total recurring-income amount must not be treated as the amount newly added by the import, because some or all of those transactions may already exist in RIMS.

Existing income-analysis services remain the authoritative financial calculation layer.

---

## 11. Source-File Provenance

The source filename is preserved on each persisted transaction.

The controlled import service verifies that:

- the physical source file basename
- the validated source filename
- the transaction `source_file`

are consistent before persistence.

This maintains transaction-level provenance without using source-file provenance as part of transaction identity.

---

## 12. Validation Boundary

Controlled transaction import requires a valid `TransactionsValidationResult`.

The import is rejected when:

- the validation result is the wrong type
- `is_valid` is false
- the parsed import result is missing
- the physical source file is missing
- the physical source filename does not match the validated filename
- the validated account is blank

Validation remains a prerequisite to persistence.

The controlled importer does not bypass the validation layer.

---

## 13. Persistence Model

New transactions are stored in a new immutable `TransactionDataset`.

When an incoming batch contains both existing and new transactions:

- Existing transactions are skipped.
- Only new transactions are placed in the new dataset.
- Previously persisted datasets remain unchanged.

When all incoming transactions are duplicates:

- No new dataset is created.
- Existing datasets remain unchanged.

This preserves the historical nature of RIMS transaction data.

---

## 14. Testing Requirements

Sprint 22D tests cover:

### TransactionRepository

- Deterministic fingerprints.
- Source-file exclusion from fingerprints.
- Different transactions producing different fingerprints.
- Adding all-new transactions.
- Skipping previously persisted transactions.
- Handling overlapping exports.
- Adding only new transactions from an overlapping export.
- Skipping duplicate transactions within one batch.
- Handling an entirely duplicate batch without creating a dataset.
- Preserving previously persisted datasets.

### ControlledTransactionImportService

- Successful transaction import.
- Import operation creation and status.
- Transaction counts.
- Income transaction counts.
- Recurring-income transaction counts.
- Duplicate source-file protection.
- Transaction-level duplicate protection.
- Invalid validation-result rejection.
- Source filename validation.
- Missing source-file rejection.
- Missing parsed import-result rejection.
- Repository failure handling.

---

## 15. Architectural Boundary

Sprint 22D establishes the following boundary:

    Validation
        ↓
    Controlled Import
        ↓
    Persistence
        ↓
    Financial Analysis

Each layer has a distinct responsibility.

The controlled import layer is an orchestration and safety layer. It does not become an alternative financial calculation engine.

Post-import reconciliation and updating of downstream portfolio and income analysis remain separate concerns and are addressed in later Sprint 22 work.
