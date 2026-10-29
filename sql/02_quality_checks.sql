
-- ==================================================
-- BANKING ETL PIPELINE
-- 02. ПРОВЕРКИ КАЧЕСТВА ДАННЫХ
-- ==================================================
-- Назначение:
-- Проверка staging и clean до аналитики.
-- Все запросы ниже только читают данные.

-- 1. Количество строк в исходных таблицах
SELECT 'customers' AS table_name, COUNT(*) AS row_count
FROM staging.customers
UNION ALL
SELECT 'accounts', COUNT(*)
FROM staging.accounts
UNION ALL
SELECT 'transactions', COUNT(*)
FROM staging.transactions;

-- 2. Проверка дубликатов ID клиентов
SELECT
    customer_id,
    COUNT(*) AS copies
FROM staging.customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- 3. Проверка дубликатов ID счетов
SELECT
    account_id,
    COUNT(*) AS copies
FROM staging.accounts
GROUP BY account_id
HAVING COUNT(*) > 1;

-- 4. Проверка дубликатов ID транзакций
SELECT
    transaction_id,
    COUNT(*) AS copies
FROM staging.transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- 5. Поиск счетов без существующего клиента
SELECT
    a.account_id,
    a.customer_id
FROM staging.accounts AS a
LEFT JOIN staging.customers AS c
    ON a.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- 6. Поиск транзакций без существующего счета
SELECT
    t.transaction_id,
    t.account_id
FROM staging.transactions AS t
LEFT JOIN staging.accounts AS a
    ON t.account_id = a.account_id
WHERE a.account_id IS NULL;

-- 7. Проверка пропущенных сумм в очищенных данных
SELECT
    transaction_id,
    amount,
    currency
FROM clean.transactions_typed
WHERE amount IS NULL;

-- 8. Проверка пропущенных дат в типизированных данных
SELECT
    transaction_id,
    transaction_ts
FROM clean.transactions_typed
WHERE transaction_ts IS NULL;

-- 9. Проверка оставшихся полных дубликатов
SELECT
    transaction_id,
    account_id,
    transaction_ts,
    amount,
    currency,
    operation_type,
    transaction_status,
    COUNT(*) AS copies
FROM clean.transactions_typed
GROUP BY
    transaction_id,
    account_id,
    transaction_ts,
    amount,
    currency,
    operation_type,
    transaction_status
HAVING COUNT(*) > 1;
