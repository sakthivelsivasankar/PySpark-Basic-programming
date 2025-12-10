/*
================================================================================
DIMENSION TABLES - VIEW DDL GENERATOR (FABRIC WAREHOUSE COMPATIBLE)
================================================================================
Purpose: Generate CREATE VIEW statements for DIM_ tables with explicit columns
         Output: DDL scripts ready for review and manual execution

Compatibility: Microsoft Fabric Warehouse (SQL Analytics Endpoint)
================================================================================

CONFIGURATION - Edit these values by search/replace:
--------------------------------------------------------------------------------
Source Schema:  ELT_ANALYTICS         (search: ELT_ANALYTICS)
Target Schema:  DATAMART_DIM          (search: DATAMART_DIM)
Table Prefix:   DIM_                  (search: DIM_)
View Prefix:    VW_                   (search: VW_)
--------------------------------------------------------------------------------

FABRIC WAREHOUSE CONSTRAINTS HANDLED:
- No cursors (uses set-based CTEs)
- No NVARCHAR(128)/NVARCHAR(MAX) (uses VARCHAR(8000))
- COLLATE Latin1_General_100_BIN2_UTF8 on all string comparisons
- CONVERT(VARCHAR(8000), ...) for sys catalog columns

================================================================================
*/

-- ============================================================================
-- SCRIPT EXECUTION
-- ============================================================================

PRINT '================================================================================';
PRINT 'DIMENSION TABLES - VIEW DDL GENERATOR';
PRINT '================================================================================';
PRINT 'Source Schema: ELT_ANALYTICS';
PRINT 'Target Schema: DATAMART_DIM';
PRINT 'Table Prefix:  DIM_';
PRINT 'View Prefix:   VW_';
PRINT '================================================================================';
PRINT '';

-- ============================================================================
-- MAIN CTE - Generate all view definitions in a single query
-- ============================================================================

WITH FilteredTables AS (
    -- Get all DIM tables from source schema
    -- To change schema: replace 'ELT_ANALYTICS' below
    -- To change prefix: replace 'DIM_%' below
    SELECT 
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        t.object_id AS ObjectId
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'DIM_%'
      -- ========================================================================
      -- IGNORE PATTERNS - Add or remove patterns as needed
      -- ========================================================================
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
),
TableColumns AS (
    -- Build column list for each table using STRING_AGG
    SELECT 
        ft.TableName,
        ft.ObjectId,
        STRING_AGG(
            '[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
            ', '
        ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList
    FROM FilteredTables ft
    INNER JOIN sys.columns c ON ft.ObjectId = c.object_id
    GROUP BY ft.TableName, ft.ObjectId
),
ViewDefinitions AS (
    -- Generate complete DDL for each view
    SELECT 
        tc.TableName,
        'VW_' + tc.TableName AS ViewName,
        tc.ColumnList,
        -- Build the complete DDL script
        '-- ============================================================================' + CHAR(13) + CHAR(10) +
        '-- VIEW: VW_' + tc.TableName + CHAR(13) + CHAR(10) +
        '-- SOURCE: ELT_ANALYTICS.' + tc.TableName + CHAR(13) + CHAR(10) +
        '-- ============================================================================' + CHAR(13) + CHAR(10) +
        CHAR(13) + CHAR(10) +
        'DROP VIEW IF EXISTS [DATAMART_DIM].[VW_' + tc.TableName + '];' + CHAR(13) + CHAR(10) +
        'GO' + CHAR(13) + CHAR(10) +
        CHAR(13) + CHAR(10) +
        'CREATE VIEW [DATAMART_DIM].[VW_' + tc.TableName + ']' + CHAR(13) + CHAR(10) +
        'AS' + CHAR(13) + CHAR(10) +
        'SELECT ' + tc.ColumnList + CHAR(13) + CHAR(10) +
        'FROM [ELT_ANALYTICS].[' + tc.TableName + '];' + CHAR(13) + CHAR(10) +
        'GO' + CHAR(13) + CHAR(10) +
        CHAR(13) + CHAR(10) AS DDLScript
    FROM TableColumns tc
)
-- Store results in temp table for output
SELECT 
    TableName,
    ViewName,
    ColumnList,
    DDLScript
INTO #DimViewDDL
FROM ViewDefinitions;

-- ============================================================================
-- DISPLAY TABLES TO PROCESS
-- ============================================================================

PRINT '=== TABLES TO PROCESS ===';
PRINT '';

SELECT TableName, ViewName FROM #DimViewDDL ORDER BY TableName;

PRINT '';
PRINT '================================================================================';
PRINT '-- GENERATED DDL STATEMENTS';
PRINT '================================================================================';
PRINT '';

-- ============================================================================
-- OUTPUT: SCHEMA CREATION
-- ============================================================================

PRINT '-- ============================================================================';
PRINT '-- STEP 1: CREATE TARGET SCHEMA (if not exists)';
PRINT '-- ============================================================================';
PRINT '';
PRINT 'IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = ''DATAMART_DIM'')';
PRINT 'BEGIN';
PRINT '    EXEC(''CREATE SCHEMA [DATAMART_DIM]'');';
PRINT 'END;';
PRINT 'GO';
PRINT '';
PRINT '-- ============================================================================';
PRINT '-- STEP 2: CREATE DIMENSION VIEWS';
PRINT '-- ============================================================================';
PRINT '';

-- ============================================================================
-- OUTPUT: VIEW DDL STATEMENTS
-- ============================================================================

SELECT DDLScript FROM #DimViewDDL ORDER BY TableName;

-- ============================================================================
-- SUMMARY
-- ============================================================================

PRINT '';
PRINT '================================================================================';
PRINT '-- GENERATION COMPLETE';
PRINT '================================================================================';

SELECT 
    'Total Views Generated: ' + CAST(COUNT(*) AS VARCHAR(10)) AS Summary
FROM #DimViewDDL;

PRINT '';
PRINT '-- Copy the DDL statements above and execute in your target environment';
PRINT '================================================================================';

-- Cleanup
DROP TABLE IF EXISTS #DimViewDDL;
