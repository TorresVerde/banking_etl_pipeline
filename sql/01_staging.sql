
-- ==================================================
-- BANKING ETL PIPELINE
-- 01. СОЗДАНИЕ STAGING-ТАБЛИЦ
-- ==================================================
-- Назначение:
-- Создание схемы staging и таблиц для загрузки
-- исходных данных из CSV.
--
-- Важно:
-- Этот скрипт создаёт структуру, но не загружает данные.
-- IF NOT EXISTS позволяет повторно запускать скрипт,
-- не пересоздавая существующие таблицы.

-- 1. Создание схемы для исходных данных
CREATE SCHEMA IF NOT EXISTS staging;

-- 2. Таблица клиентов
CREATE TABLE IF NOT EXISTS staging.customers (
    customer_id TEXT,
    full_name TEXT,
    birth_date TEXT,
    registration_date TEXT,
    customer_status TEXT
);

-- 3. Таблица счетов
CREATE TABLE IF NOT EXISTS staging.accounts (
    account_id TEXT,
    customer_id TEXT,
    account_type TEXT,
    currency TEXT,
    open_date TEXT,
    account_status TEXT
);

-- 4. Таблица транзакций
CREATE TABLE IF NOT EXISTS staging.transactions (
    transaction_id TEXT,
    account_id TEXT,
    transaction_ts TEXT,
    amount TEXT,
    currency TEXT,
    operation_type TEXT,
    transaction_status TEXT
);
