-- =============================================================================
-- Brazilian Running Results — V1: Create Tables
-- =============================================================================

-- -----------------------------------------------------------------------------
-- State
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS state (
    id              SMALLSERIAL     PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    abbreviation    CHAR(2)         NOT NULL,

    CONSTRAINT uq_state_name         UNIQUE (name),
    CONSTRAINT uq_state_abbreviation UNIQUE (abbreviation)
);

-- -----------------------------------------------------------------------------
-- City
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS city (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(150)    NOT NULL,
    state_id    SMALLINT        NOT NULL,

    CONSTRAINT fk_city_state    FOREIGN KEY (state_id) REFERENCES state (id),
    CONSTRAINT uq_city_state    UNIQUE (name, state_id)
);

-- -----------------------------------------------------------------------------
-- Date dimension
-- Separada para permitir enriquecimento (feriados, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS date (
    id              SERIAL      PRIMARY KEY,
    date            DATE        NOT NULL,
    day             SMALLINT    NOT NULL    CHECK (day BETWEEN 1 AND 31),
    month           SMALLINT    NOT NULL    CHECK (month BETWEEN 1 AND 12),
    year            SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL    CHECK (day_of_week BETWEEN 1 AND 7),
    -- 1=Segunda ... 7=Domingo
    is_holiday      BOOLEAN     NOT NULL    DEFAULT FALSE,

    CONSTRAINT uq_date UNIQUE (date)
);

-- -----------------------------------------------------------------------------
-- Event 
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event (
    id          SERIAL          PRIMARY KEY,
    slug        VARCHAR(255)    NOT NULL,   -- "maratona-de-sao-paulo-2023"
    hash_slug     CHAR(32)        NOT NULL,   -- MD5 do slug
    name        VARCHAR(255)    NOT NULL,
    city_id     INT             NOT NULL,
    date_id     INT             NOT NULL,
    created_at   TIMESTAMPTZ    NOT NULL    DEFAULT NOW(),

    CONSTRAINT fk_event_city     FOREIGN KEY (city_id)   REFERENCES city (id),
    CONSTRAINT fk_event_date     FOREIGN KEY (date_id)   REFERENCES date (id),
    CONSTRAINT uq_event_hash     UNIQUE (hash_slug)
);

-- -----------------------------------------------------------------------------
-- Modality (Modalidade)
-- Descoberta a partir da página do evento na etapa de scrape.
-- distance_km é a versão normalizada; raw_category_name preserva o nome original.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modality (
    id                  SERIAL          PRIMARY KEY,
    event_id            INT             NOT NULL,
    distance_km         NUMERIC(6,2)    NOT NULL    CHECK (distance_km > 0),
    is_pcd              BOOLEAN         NOT NULL    DEFAULT FALSE,
    raw_category_name   VARCHAR(255)    NOT NULL,

    CONSTRAINT fk_modality_event     FOREIGN KEY (event_id) REFERENCES event (id),
    CONSTRAINT uq_modality_event_raw UNIQUE (event_id, raw_category_name)
);

ALTER TABLE modality ADD COLUMN IF NOT EXISTS distance_km NUMERIC(6,2);
ALTER TABLE modality ADD COLUMN IF NOT EXISTS is_pcd BOOLEAN;
ALTER TABLE modality ADD COLUMN IF NOT EXISTS raw_category_name VARCHAR(255);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'modality' AND column_name = 'distance'
    ) THEN
        EXECUTE 'UPDATE modality SET distance_km = COALESCE(distance_km, distance::NUMERIC(6,2)) WHERE distance_km IS NULL';
    END IF;
END $$;

UPDATE modality
SET is_pcd = FALSE
WHERE is_pcd IS NULL;

UPDATE modality
SET raw_category_name = CONCAT(TRIM(TRAILING '.00' FROM TRIM(TRAILING '0' FROM distance_km::TEXT)), ' KM')
WHERE raw_category_name IS NULL;

ALTER TABLE modality ALTER COLUMN distance_km SET NOT NULL;
ALTER TABLE modality ALTER COLUMN is_pcd SET NOT NULL;
ALTER TABLE modality ALTER COLUMN is_pcd SET DEFAULT FALSE;
ALTER TABLE modality ALTER COLUMN raw_category_name SET NOT NULL;
ALTER TABLE modality DROP CONSTRAINT IF EXISTS uq_modality_event;
ALTER TABLE modality DROP CONSTRAINT IF EXISTS uq_modality_event_raw;
ALTER TABLE modality ADD CONSTRAINT uq_modality_event_raw UNIQUE (event_id, raw_category_name);
ALTER TABLE modality DROP COLUMN IF EXISTS finishers;
ALTER TABLE modality DROP COLUMN IF EXISTS distance;

-- -----------------------------------------------------------------------------
-- Category (Categoria)
-- Ex: M1624, F2029, M3039...
-- Tabela global — categorias são reaproveitadas entre corridas
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS category (
    id      SMALLSERIAL     PRIMARY KEY,
    name    VARCHAR(20)     NOT NULL,

    CONSTRAINT uq_category_name UNIQUE (name)
);

-- -----------------------------------------------------------------------------
-- Result (Resultado)
-- Consolidação de corrida + modalidade + categoria + atleta
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS result (
    id              BIGSERIAL       PRIMARY KEY,
    event_id         INT             NOT NULL,
    modality_id     INT             NOT NULL,
    category_id     SMALLINT        NOT NULL,
    overall_pos     INT             NOT NULL    CHECK (overall_pos > 0),
    bib_number      VARCHAR(20),
    athlete_name    VARCHAR(255)    NOT NULL,
    team            VARCHAR(255),
    pace            INTERVAL,
    finish_time     INTERVAL        NOT NULL,
    gap             INTERVAL,

    CONSTRAINT fk_result_event       FOREIGN KEY (event_id)       REFERENCES event (id),
    CONSTRAINT fk_result_modality   FOREIGN KEY (modality_id)   REFERENCES modality (id),
    CONSTRAINT fk_result_category   FOREIGN KEY (category_id)   REFERENCES category (id),

    -- Evita duplicatas na reingestão
    CONSTRAINT uq_result UNIQUE (modality_id, category_id, bib_number)
);

-- -----------------------------------------------------------------------------
-- Extraction Job
-- 1 job por evento — controle macro
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS extraction_job (
    id          SERIAL      PRIMARY KEY,
    event_id    INT         NOT NULL REFERENCES event(id),
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'completed', 'failed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_job_event UNIQUE (event_id)
);

-- -----------------------------------------------------------------------------
-- Extraction Task
-- 1 task por target descoberto (modality_id x gender)
-- source_url guarda o link exato descoberto no HTML.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS extraction_task (
    id              SERIAL      PRIMARY KEY,
    job_id          INT         NOT NULL REFERENCES extraction_job(id),
    modality_id     INT         NOT NULL REFERENCES modality(id),
    gender          CHAR(1)     NOT NULL CHECK (gender IN ('M', 'F')),
    source_url      TEXT        NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'completed', 'failed')),
    s3_path         TEXT,
    redshift_loaded BOOLEAN     NOT NULL DEFAULT FALSE,
    row_count       INT,
    attempts        SMALLINT    NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_task UNIQUE (job_id, modality_id, gender)
);

ALTER TABLE extraction_task ADD COLUMN IF NOT EXISTS source_url TEXT;
UPDATE extraction_task
SET source_url = ''
WHERE source_url IS NULL;
ALTER TABLE extraction_task ALTER COLUMN source_url SET NOT NULL;

CREATE INDEX idx_job_status       ON extraction_job(status);
CREATE INDEX idx_task_status      ON extraction_task(status);
CREATE INDEX idx_task_pending     ON extraction_task(status)
    WHERE status IN ('pending', 'failed');
CREATE INDEX idx_task_s3_pending  ON extraction_task(redshift_loaded)
    WHERE status = 'completed' AND redshift_loaded = FALSE;