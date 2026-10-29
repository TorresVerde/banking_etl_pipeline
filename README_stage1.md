# Banking ETL Pipeline — Stage 1: Source Files

All records in these files are synthetic and created for learning. They do not represent real customers or bank transactions.

## Files
- `customers.csv`: customer master data
- `accounts.csv`: account master data
- `transactions.csv`: transaction events

## Encoding and format
- CSV, UTF-8 with BOM (`utf-8-sig`) for convenient opening in Excel
- comma delimiter
- dates use ISO format `YYYY-MM-DD`
- transaction timestamps use `YYYY-MM-DD HH:MM:SS`
- monetary amounts use decimal point and two fractional digits where provided; blank amount represents a deliberate missing value

## Intended relationships
- `accounts.customer_id` -> `customers.customer_id`
- `transactions.account_id` -> `accounts.account_id`

## Deliberate data-quality defects in `transactions.csv`
These are intentional test cases, not accidental mistakes:
1. Missing amount in transaction `T30008`
2. Unknown account reference `A2999` in transaction `T30011`
3. Duplicate transaction ID `T30014`
4. Invalid timestamp `2026-10-10 29:45:20` in transaction `T30017`
5. Unexpected operation type `CASHIN` in transaction `T30019`

We will detect, document, and handle these defects in later stages rather than silently correcting the source.
