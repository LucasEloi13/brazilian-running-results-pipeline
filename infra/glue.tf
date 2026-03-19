# =============================================================================
# AWS Glue Data Catalog — Brazilian Running Results
# =============================================================================

locals {
  glue_db_name    = "running_results"
  s3_bucket_id    = aws_s3_bucket.running_results.bucket
  dims_prefix     = "dims"
  results_prefix  = "results"

  parquet_input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
  parquet_output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
  parquet_serde         = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
}

# -----------------------------------------------------------------------------
# Glue Database
# -----------------------------------------------------------------------------

resource "aws_glue_catalog_database" "running_results" {
  name        = local.glue_db_name
  description = "Brazilian Running Results — dimensions (Parquet) and raw CSV results"

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Helper: shared Parquet SerDe block (reused via module-level locals)
# Each table resource must repeat the block — Terraform does not support
# dynamic nested blocks — so we define the values in locals and reference them.
# -----------------------------------------------------------------------------

# =============================================================================
# Dimension Tables (Parquet)
# =============================================================================

# --- dim_state ----------------------------------------------------------------

resource "aws_glue_catalog_table" "dim_state" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_state"
  description   = "Brazilian states — exported once from the OLTP state table"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification                   = "parquet"
    "parquet.compression"            = "SNAPPY"
    "projection.enabled"             = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/state/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "smallint"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "abbreviation"
      type = "string"
    }
  }
}

# --- dim_city -----------------------------------------------------------------

resource "aws_glue_catalog_table" "dim_city" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_city"
  description   = "Brazilian cities — exported weekly from the OLTP city table"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/city/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "int"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "state_id"
      type = "smallint"
    }
  }
}

# --- dim_date -----------------------------------------------------------------

resource "aws_glue_catalog_table" "dim_date" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_date"
  description   = "Date dimension — exported weekly from the OLTP date table"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/date/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "int"
    }
    columns {
      name = "date"
      type = "date"
    }
    columns {
      name = "day"
      type = "smallint"
    }
    columns {
      name = "month"
      type = "smallint"
    }
    columns {
      name = "year"
      type = "smallint"
    }
    columns {
      name = "day_of_week"
      type = "smallint"
    }
    columns {
      name = "is_holiday"
      type = "boolean"
    }
  }
}

# --- dim_event ----------------------------------------------------------------

resource "aws_glue_catalog_table" "dim_event" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_event"
  description   = "Running events — exported on every pipeline run from the OLTP event table"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/event/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "int"
    }
    columns {
      name = "slug"
      type = "string"
    }
    columns {
      name = "hash_slug"
      type = "string"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "city_id"
      type = "int"
    }
    columns {
      name = "date_id"
      type = "int"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
  }
}

# --- dim_modality -------------------------------------------------------------

resource "aws_glue_catalog_table" "dim_modality" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_modality"
  description   = "Race modalities (distance / PCD flag) — exported on every pipeline run"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/modality/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "int"
    }
    columns {
      name = "event_id"
      type = "int"
    }
    columns {
      name = "distance_km"
      type = "double"
    }
    columns {
      name = "is_pcd"
      type = "boolean"
    }
    columns {
      name = "raw_category_name"
      type = "string"
    }
  }
}

# --- dim_extraction_job -------------------------------------------------------

resource "aws_glue_catalog_table" "dim_extraction_job" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_extraction_job"
  description   = "Extraction job control table — all jobs exported on every pipeline run"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/extraction_job/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "int"
    }
    columns {
      name = "event_id"
      type = "int"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
    columns {
      name = "updated_at"
      type = "timestamp"
    }
  }
}

# --- dim_extraction_task ------------------------------------------------------

resource "aws_glue_catalog_table" "dim_extraction_task" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_extraction_task"
  description   = "Extraction task control table — only completed tasks exported"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/extraction_task/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "id"
      type = "int"
    }
    columns {
      name = "job_id"
      type = "int"
    }
    columns {
      name = "modality_id"
      type = "int"
    }
    columns {
      name = "gender"
      type = "string"
    }
    columns {
      name = "source_url"
      type = "string"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "s3_path"
      type = "string"
    }
    columns {
      name = "redshift_loaded"
      type = "boolean"
    }
    columns {
      name = "row_count"
      type = "int"
    }
    columns {
      name = "attempts"
      type = "smallint"
    }
    columns {
      name = "last_attempt_at"
      type = "timestamp"
    }
    columns {
      name = "error_msg"
      type = "string"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
  }
}

# =============================================================================
# Raw Results CSV Table
#
# All 20 columns are present in the CSV data (no Hive partitioning).
# Stored at S3 under results/ with state/city/modality/pcd/gender/event in the path for
# organization, but these values are also in the data itself.
#
# Columns: pipeline metadata (7) + scraped fields (7) + location metadata (6).
# All values are written as strings by EventResultStorage.upload_to_s3().
# =============================================================================

resource "aws_glue_catalog_table" "results_csv" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "results_csv"
  description   = "Raw race results scraped from openresults.run, stored as Hive-partitioned CSV"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification            = "csv"
    "skip.header.line.count"  = "1"
    "projection.enabled"      = "false"
    "has_encrypted_data"      = "false"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.results_prefix}/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters = {
        "separatorChar" = ","
        "quoteChar"     = "\""
        "escapeChar"    = "\\"
      }
    }

    # --- CSV column order: MUST MATCH HEADER EXACTLY ---
    # Header: geral,cat,numero,nome,equipe,pace,tempo,gap,raw_row_id,overall,category,bib,athlete_name,team,finish_time,job_id,task_id,event_id,modality_id,gender,distance_km,is_pcd,raw_category_name
    columns {
      name    = "geral"
      type    = "int"
      comment = "Overall position (raw from HTML)"
    }
    columns {
      name    = "cat"
      type    = "string"
      comment = "Category code (raw from HTML)"
    }
    columns {
      name    = "numero"
      type    = "string"
      comment = "Bib number (raw from HTML)"
    }
    columns {
      name    = "nome"
      type    = "string"
      comment = "Athlete name (raw from HTML)"
    }
    columns {
      name    = "equipe"
      type    = "string"
      comment = "Team/club (raw from HTML)"
    }
    columns {
      name    = "pace"
      type    = "string"
      comment = "Pace per km (raw from HTML)"
    }
    columns {
      name    = "tempo"
      type    = "string"
      comment = "Finish time (raw from HTML)"
    }
    columns {
      name    = "gap"
      type    = "string"
      comment = "Gap to winner (raw from HTML)"
    }
    columns {
      name    = "raw_row_id"
      type    = "string"
      comment = "HTML row id attribute"
    }
    columns {
      name    = "overall"
      type    = "string"
      comment = "Normalized overall position"
    }
    columns {
      name    = "category"
      type    = "string"
      comment = "Normalized category"
    }
    columns {
      name    = "bib"
      type    = "string"
      comment = "Normalized bib number"
    }
    columns {
      name    = "athlete_name"
      type    = "string"
      comment = "Normalized athlete name"
    }
    columns {
      name    = "team"
      type    = "string"
      comment = "Normalized team"
    }
    columns {
      name    = "finish_time"
      type    = "string"
      comment = "Normalized finish time"
    }
    columns {
      name    = "job_id"
      type    = "string"
      comment = "Extraction job ID (FK to dim_extraction_job)"
    }
    columns {
      name    = "task_id"
      type    = "string"
      comment = "Extraction task ID (FK to dim_extraction_task)"
    }
    columns {
      name    = "event_id"
      type    = "string"
      comment = "Event ID (FK to dim_event)"
    }
    columns {
      name    = "modality_id"
      type    = "string"
      comment = "Modality ID (FK to dim_modality)"
    }
    columns {
      name    = "gender"
      type    = "string"
      comment = "M | F"
    }
    columns {
      name    = "distance_km"
      type    = "string"
      comment = "Formatted distance e.g. 5k, 42k"
    }
    columns {
      name    = "is_pcd"
      type    = "string"
      comment = "true | false (PCD flag)"
    }
    columns {
      name    = "raw_category_name"
      type    = "string"
      comment = "Original category label from event page"
    }
  }

  # Partition columns derived from S3 path structure
  partition_keys {
    name    = "state"
    type    = "string"
    comment = "State abbreviation slug (e.g. sp, rj, ba)"
  }
  partition_keys {
    name    = "city"
    type    = "string"
    comment = "City name slug"
  }
  partition_keys {
    name    = "modality"
    type    = "string"
    comment = "Formatted distance slug (e.g. 5k, 42k)"
  }
  partition_keys {
    name    = "pcd"
    type    = "string"
    comment = "true | false"
  }
  partition_keys {
    name    = "gender_partition"
    type    = "string"
    comment = "M | F (from S3 partition path)"
  }
  partition_keys {
    name    = "event"
    type    = "string"
    comment = "Event name slug"
  }
}

# =============================================================================
# dim_results — Parquet version of results_csv
#
# Populated and kept fresh by infra/scripts/csv_to_parquet.py (Athena).
# Strategy: incremental INSERT INTO by job_id.  Full refresh available via
#           --full-refresh flag.
#
# S3 layout: dims/results/<athena-generated>.parquet
# Column order must match the SELECT in csv_to_parquet.py exactly.
# =============================================================================

resource "aws_glue_catalog_table" "dim_results" {
  database_name = aws_glue_catalog_database.running_results.name
  name          = "dim_results"
  description   = "Race results in Parquet — incrementally loaded from results_csv via Athena INSERT INTO"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
    # Athena INSERT INTO writes here; no partitions so no MSCK needed on this table.
    "EXTERNAL"            = "TRUE"
  }

  storage_descriptor {
    location      = "s3://${local.s3_bucket_id}/${local.dims_prefix}/results/"
    input_format  = local.parquet_input_format
    output_format = local.parquet_output_format

    ser_de_info {
      serialization_library = local.parquet_serde
      parameters            = { "serialization.format" = "1" }
    }

    # ---- order must match SELECT in csv_to_parquet.py ----
    # Partition columns (from S3 path)
    columns {
      name    = "state"
      type    = "string"
      comment = "State abbreviation slug"
    }
    columns {
      name    = "city"
      type    = "string"
      comment = "City name slug"
    }
    columns {
      name    = "modality"
      type    = "string"
      comment = "Formatted distance slug (e.g. 5k)"
    }
    columns {
      name    = "pcd"
      type    = "string"
      comment = "true|false"
    }
    columns {
      name    = "gender_partition"
      type    = "string"
      comment = "M|F (from S3 path partition)"
    }
    columns {
      name    = "event"
      type    = "string"
      comment = "Event slug"
    }
    # CSV columns (in exact header order)
    columns {
      name    = "geral"
      type    = "string"
      comment = "Overall position (raw from HTML)"
    }
    columns {
      name    = "cat"
      type    = "string"
      comment = "Category code (raw)"
    }
    columns {
      name    = "numero"
      type    = "string"
      comment = "Bib number (raw)"
    }
    columns {
      name    = "nome"
      type    = "string"
      comment = "Athlete name (raw)"
    }
    columns {
      name    = "equipe"
      type    = "string"
      comment = "Team (raw)"
    }
    columns {
      name    = "pace"
      type    = "int"
      comment = "Pace in seconds"
    }
    columns {
      name    = "tempo"
      type    = "int"
      comment = "Finish time in seconds"
    }
    columns {
      name    = "gap"
      type    = "int"
      comment = "Gap to winner in seconds"
    }
    columns {
      name    = "raw_row_id"
      type    = "int"
      comment = "HTML row id"
    }
    columns {
      name    = "overall"
      type    = "int"
      comment = "Overall position"
    }
    columns {
      name    = "category"
      type    = "string"
      comment = "Category"
    }
    columns {
      name    = "bib"
      type    = "string"
      comment = "Bib number"
    }
    columns {
      name    = "athlete_name"
      type    = "string"
      comment = "Athlete name"
    }
    columns {
      name    = "team"
      type    = "string"
      comment = "Team"
    }
    columns {
      name    = "finish_time"
      type    = "int"
      comment = "Finish time in seconds"
    }
    columns {
      name    = "job_id"
      type    = "int"
      comment = "Job ID"
    }
    columns {
      name    = "task_id"
      type    = "int"
      comment = "Task ID"
    }
    columns {
      name    = "event_id"
      type    = "int"
      comment = "Event ID"
    }
    columns {
      name    = "modality_id"
      type    = "int"
      comment = "Modality ID"
    }
    columns {
      name    = "gender"
      type    = "string"
      comment = "M|F (from CSV, redundant with partition)"
    }
    columns {
      name    = "distance_km"
      type    = "string"
      comment = "Distance"
    }
    columns {
      name    = "is_pcd"
      type    = "boolean"
      comment = "PCD flag"
    }
    columns {
      name    = "raw_category_name"
      type    = "string"
      comment = "Original category label"
    }
  }
}
