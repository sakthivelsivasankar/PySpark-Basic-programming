/*
================================================================================
DIMENSION TABLES - VIEW DDL GENERATOR (FABRIC WAREHOUSE COMPATIBLE)
================================================================================
Purpose: Generate and optionally execute CREATE VIEW statements for DIM_ tables

Compatibility: Microsoft Fabric Warehouse (SQL Analytics Endpoint)
================================================================================

HOW TO USE:
--------------------------------------------------------------------------------
1. PREVIEW MODE: Run Section 1 and Section 2 to validate DDL before execution
2. EXECUTE MODE: Run Section 3 to create schema, then Section 4 to create views
--------------------------------------------------------------------------------

CONFIGURATION - Edit these values by search/replace:
--------------------------------------------------------------------------------
Source Schema:  ELT_ANALYTICS         (search: ELT_ANALYTICS)
Target Schema:  DATAMART_DIM          (search: DATAMART_DIM)
Table Prefix:   DIM_                  (search: DIM_)
View Prefix:    VW_                   (search: VW_)
--------------------------------------------------------------------------------
*/

-- ============================================================================
-- SECTION 1: PREVIEW - Tables to be processed
-- ============================================================================
-- Run this to see which tables will have views created

SELECT 
    'PREVIEW' AS Mode,
    CONVERT(VARCHAR(8000), t.name) AS TableName,
    'VW_' + CONVERT(VARCHAR(8000), t.name) AS ViewName,
    'DATAMART_DIM' AS TargetSchema
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'DIM_%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%TEMP%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%temp%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%test%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%TEST%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%BACKUP%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%backup%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%Archive%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%ARCHIVE%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%STG%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%DUMMY%'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_BKP'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_OLS'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_CLS'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_VY'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_TW'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_T'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_1'
  AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_2'
ORDER BY TableName;

-- ============================================================================
-- SECTION 2: PREVIEW - Generated DDL Statements (for validation)
-- ============================================================================
-- Run this to see the exact DDL that will be executed

SELECT 
    sub.TableName,
    'VW_' + sub.TableName AS ViewName,
    'DROP VIEW IF EXISTS [DATAMART_DIM].[VW_' + sub.TableName + ']' AS DropStatement,
    'CREATE VIEW [DATAMART_DIM].[VW_' + sub.TableName + '] AS SELECT ' + sub.ColumnList + ' FROM [ELT_ANALYTICS].[' + sub.TableName + ']' AS CreateStatement
FROM (
    SELECT 
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        STRING_AGG(
            '[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
            ', '
        ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'DIM_%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%TEMP%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%temp%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%test%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%TEST%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%BACKUP%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%backup%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%Archive%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%ARCHIVE%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%STG%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%DUMMY%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_BKP'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_OLS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_CLS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_VY'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_TW'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_T'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_1'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_2'
    GROUP BY t.name
) sub
ORDER BY sub.TableName;


-- ****************************************************************************
-- ****************************************************************************
-- EXECUTE MODE - Run sections below to CREATE VIEWS
-- ****************************************************************************
-- ****************************************************************************

-- ============================================================================
-- SECTION 3: EXECUTE - Create Target Schema (Run once)
-- ============================================================================
-- Uncomment and run this section first

/*
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'DATAMART_DIM')
BEGIN
    EXEC('CREATE SCHEMA [DATAMART_DIM]');
END;
*/

-- ============================================================================
-- SECTION 4: EXECUTE - Create All Dimension Views
-- ============================================================================
-- Uncomment and run this section to create all views
-- This executes DROP + CREATE for each view dynamically

/*
EXEC((
    SELECT STRING_AGG(
        'DROP VIEW IF EXISTS [DATAMART_DIM].[VW_' + sub.TableName + ']; ' +
        'CREATE VIEW [DATAMART_DIM].[VW_' + sub.TableName + '] AS SELECT ' + sub.ColumnList + ' FROM [ELT_ANALYTICS].[' + sub.TableName + ']; ',
        ' '
    )
    FROM (
        SELECT 
            CONVERT(VARCHAR(8000), t.name) AS TableName,
            STRING_AGG(
                '[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
                ', '
            ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList
        FROM sys.tables t
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        INNER JOIN sys.columns c ON t.object_id = c.object_id
        WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'DIM_%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%TEMP%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%temp%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%test%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%TEST%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%BACKUP%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%backup%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%Archive%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%ARCHIVE%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%STG%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%DUMMY%'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_BKP'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_OLS'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_CLS'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_VY'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_TW'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_T'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_1'
          AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_2'
        GROUP BY t.name
    ) sub
));
*/

-- ============================================================================
-- SECTION 5: VERIFY - Check created views
-- ============================================================================
-- Run this after execution to verify views were created

/*
SELECT 
    s.name AS SchemaName,
    v.name AS ViewName,
    v.create_date AS CreatedDate
FROM sys.views v
INNER JOIN sys.schemas s ON v.schema_id = s.schema_id
WHERE s.name = 'DATAMART_DIM'
ORDER BY v.name;
*/
