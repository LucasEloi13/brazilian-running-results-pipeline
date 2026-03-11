-- =============================================================================
-- Brazilian Running Results — RESET: Drop all tables
-- =============================================================================
-- AVISO: Este script destrói TODOS os dados!
-- Use apenas com --reset flag em run_migration.py
-- =============================================================================

-- Drop tables em ordem inversa das constraints (foreign keys first)
DROP TABLE IF EXISTS extraction_task CASCADE;
DROP TABLE IF EXISTS extraction_job CASCADE;
DROP TABLE IF EXISTS result CASCADE;
DROP TABLE IF EXISTS modality CASCADE;
DROP TABLE IF EXISTS event CASCADE;
DROP TABLE IF EXISTS city CASCADE;
DROP TABLE IF EXISTS date CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS state CASCADE;
