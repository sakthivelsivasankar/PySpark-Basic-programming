/*
================================================================================
DIMENSION TABLES - VIEW DDL GENERATOR (FABRIC WAREHOUSE COMPATIBLE)
================================================================================
Purpose: Generate CREATE VIEW statements for DIM_ tables with explicit columns

Compatibility: Microsoft Fabric Warehouse (SQL Analytics Endpoint)
================================================================================

HOW TO USE:
--------------------------------------------------------------------------------
1. PREVIEW MODE: Run Section 1 to see tables and validate
2. EXECUTE MODE: Run Section 2, copy all rows from DDL column, execute
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

SELECT 
    ROW_NUMBER() OVER (ORDER BY CONVERT(VARCHAR(8000), t.name)) AS RowNum,
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
-- SECTION 2: EXECUTE - DDL Statements (copy all rows and execute)
-- ============================================================================
-- Instructions:
-- 1. Run this query
-- 2. Select all rows in the DDL column
-- 3. Copy to a new query window
-- 4. Execute the copied DDL

-- Schema creation
SELECT 0 AS Seq, 'SCHEMA' AS Type, 'Schema' AS ViewName,
'IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = ''DATAMART_DIM'') EXEC(''CREATE SCHEMA [DATAMART_DIM]'');
GO' AS DDL

UNION ALL

-- All view DDL statements with GO separators
SELECT 
    sub.Seq,
    'VIEW' AS Type,
    sub.ViewName,
    'DROP VIEW IF EXISTS [DATAMART_DIM].[' + sub.ViewName + '];
GO
CREATE VIEW [DATAMART_DIM].[' + sub.ViewName + '] AS SELECT ' + sub.ColumnList + ' FROM [ELT_ANALYTICS].[' + sub.TableName + '];
GO' AS DDL
FROM (
    SELECT 
        ROW_NUMBER() OVER (ORDER BY CONVERT(VARCHAR(8000), t.name)) AS Seq,
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        'VW_' + CONVERT(VARCHAR(8000), t.name) AS ViewName,
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
ORDER BY Seq;


-- ============================================================================
-- SECTION 3: VERIFY - Check created views
-- ============================================================================
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
