
-- ============================================================
-- Раздел 75. Безопасная трансформация банковских транзакций
-- Файл: sql/03_transformations.sql
--
-- Все изменения clean выполняются одной транзакцией.
-- При ошибке изменения можно откатить целиком.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS clean;

-- Создаём таблицы, если они ещё не существуют.
-- Существующие таблицы и их структуру не пересоздаём.

CREATE TABLE IF NOT EXISTS clean.transactions (
    transaction_id       TEXT,
    account_id           TEXT,
    transaction_ts       TEXT,
    amount               TEXT,
    currency             TEXT,
    operation_type       TEXT,
    transaction_status   TEXT
);

CREATE TABLE IF NOT EXISTS clean.transactions_typed (
    transaction_id       TEXT,
    account_id           TEXT,
    transaction_ts       TIMESTAMP,
    amount               NUMERIC,
    currency             TEXT,
    operation_type       TEXT,
    transaction_status   TEXT
);

-- Начинаем общую транзакцию для обеих таблиц.
-- TRUNCATE не затрагивает staging.

BEGIN;

TRUNCATE TABLE
    clean.transactions_typed,
    clean.transactions;

-- Шаг 1. Удаляем полные дубликаты.

INSERT INTO clean.transactions (
    transaction_id,
    account_id,
    transaction_ts,
    amount,
    currency,
    operation_type,
    transaction_status
)
SELECT DISTINCT
    transaction_id,
    account_id,
    transaction_ts,
    amount,
    currency,
    operation_type,
    transaction_status
FROM staging.transactions;

-- Шаг 2. Типизируем дату и сумму.
-- Для T30017 дата остаётся NULL до подтверждения формата.

INSERT INTO clean.transactions_typed (
    transaction_id,
    account_id,
    transaction_ts,
    amount,
    currency,
    operation_type,
    transaction_status
)
SELECT
    transaction_id,
    account_id,
    CASE
        WHEN transaction_id = 'T30017'
            THEN NULL
        ELSE TO_TIMESTAMP(
            NULLIF(TRIM(transaction_ts), ''),
            'DD.MM.YYYY HH24:MI'
        )::TIMESTAMP
    END,
    NULLIF(TRIM(amount), '')::NUMERIC,
    currency,
    operation_type,
    transaction_status
FROM clean.transactions;

COMMIT;
