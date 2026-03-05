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

    CONSTRAINT fk_event_city     FOREIGN KEY (city_id)   REFERENCES city (id),
    CONSTRAINT fk_event_date     FOREIGN KEY (date_id)   REFERENCES date (id),
    CONSTRAINT uq_event_hash     UNIQUE (hash_slug)
);

-- -----------------------------------------------------------------------------
-- Modality (Modalidade)
-- Cada corrida pode ter múltiplas distâncias (5, 10, 21, 42...)
-- distance armazena só o número em km, sem o "K"
-- finishers é o total de finishers naquela modalidade
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modality (
    id          SERIAL      PRIMARY KEY,
    event_id     INT         NOT NULL,
    distance    SMALLINT    NOT NULL    CHECK (distance > 0),
    finishers   INT                     CHECK (finishers >= 0),

    CONSTRAINT fk_modality_event     FOREIGN KEY (event_id) REFERENCES event (id),
    CONSTRAINT uq_modality_event     UNIQUE (event_id, distance)
);

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