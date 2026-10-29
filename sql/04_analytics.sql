
-- ============================================================
-- Раздел 59. Аналитический слой банковского ETL
-- Файл: sql/04_analytics.sql
--
-- Назначение:
-- 1. Сводная аналитика по клиентам.
-- 2. Контроль качества банковских транзакций.
--
-- Зависимости:
-- staging.customers
-- staging.accounts
-- clean.transactions_typed
-- ============================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- ------------------------------------------------------------
-- Шаг 1. Сводка по клиентам
-- ------------------------------------------------------------
-- Для каждого клиента рассчитываем количество счетов,
-- успешных транзакций и суммы по валютам.
-- Учитываем только транзакции со статусом SUCCESS.

CREATE OR REPLACE VIEW analytics.customer_summary AS
SELECT
    c.customer_id,
    c.full_name,

    COUNT(DISTINCT a.account_id) AS account_count,

    COUNT(DISTINCT t.transaction_id)
        FILTER (
            WHERE t.transaction_status = 'SUCCESS'
        ) AS successful_transactions,

    COUNT(t.amount)
        FILTER (
            WHERE t.transaction_status = 'SUCCESS'
        ) AS successful_transactions_with_amount,

    SUM(t.amount)
        FILTER (
            WHERE t.transaction_status = 'SUCCESS'
              AND t.currency = 'UZS'
        ) AS successful_amount_uzs,

    SUM(t.amount)
        FILTER (
            WHERE t.transaction_status = 'SUCCESS'
              AND t.currency = 'USD'
        ) AS successful_amount_usd

FROM staging.customers c

LEFT JOIN staging.accounts a
    ON c.customer_id = a.customer_id

LEFT JOIN clean.transactions_typed t
    ON a.account_id = t.account_id

GROUP BY
    c.customer_id,
    c.full_name;


-- ------------------------------------------------------------
-- Шаг 2. Отчёт о проблемах качества транзакций
-- ------------------------------------------------------------
-- Выявляем:
-- MISSING_AMOUNT             — нет суммы;
-- MISSING_AMOUNT_AND_ACCOUNT — нет суммы и счёта;
-- ACCOUNT_NOT_FOUND          — счёт отсутствует в справочнике;
-- MISSING_OR_UNPARSED_DATE   — дата отсутствует или не разобрана.
--
-- Проверка счёта выполняется через LEFT JOIN:
-- отсутствие совпадения означает, что счёт не найден.

CREATE OR REPLACE VIEW analytics.transaction_quality_issues AS
SELECT
    t.transaction_id,
    t.account_id,
    t.transaction_ts,
    t.amount,
    t.currency,
    t.operation_type,
    t.transaction_status,

    CASE
        WHEN t.amount IS NULL
             AND a.account_id IS NULL
            THEN 'MISSING_AMOUNT_AND_ACCOUNT'

        WHEN t.amount IS NULL
            THEN 'MISSING_AMOUNT'

        WHEN a.account_id IS NULL
            THEN 'ACCOUNT_NOT_FOUND'

        WHEN t.transaction_ts IS NULL
            THEN 'MISSING_OR_UNPARSED_DATE'

        ELSE NULL
    END AS issue_type

FROM clean.transactions_typed t

LEFT JOIN staging.accounts a
    ON t.account_id = a.account_id

WHERE t.amount IS NULL
   OR a.account_id IS NULL
   OR t.transaction_ts IS NULL;
