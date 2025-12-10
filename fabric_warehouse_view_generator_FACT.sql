/*
================================================================================
FACT TABLES - VIEW DDL GENERATOR WITH ROW-LEVEL SECURITY
(FABRIC WAREHOUSE COMPATIBLE)
================================================================================
Purpose: Generate CREATE VIEW statements for FACT_ tables with RLS security joins
         Output: DDL scripts ready for review and manual execution

Compatibility: Microsoft Fabric Warehouse (SQL Analytics Endpoint)
================================================================================

CONFIGURATION - Edit these values by search/replace:
--------------------------------------------------------------------------------
Source Schema:  ELT_ANALYTICS         (search: ELT_ANALYTICS)
Target Schema:  DATAMART_FACT         (search: DATAMART_FACT)
Table Prefix:   FACT_                 (search: FACT_)
View Prefix:    VW_                   (search: VW_)
--------------------------------------------------------------------------------

FABRIC WAREHOUSE CONSTRAINTS HANDLED:
- No cursors (uses set-based CTEs)
- No NVARCHAR(128)/NVARCHAR(MAX) (uses VARCHAR(8000))
- COLLATE Latin1_General_100_BIN2_UTF8 on all string comparisons
- CONVERT(VARCHAR(8000), ...) for sys catalog columns
- RLS config via inline VALUES CTE (not temp tables)

ROW-LEVEL SECURITY PATTERNS:
--------------------------------------------------------------------------------
1. DIRECT JOIN: fact.[GeoColumn] → WTWSecurityGEO.GeoKey
                fact.[SegColumn] → WTWSecuritySEG.SegKey

2. BRIDGE JOIN: fact → DIM_TABLE → WTWSecurityGEO/WTWSecuritySEG
   (via DIM_PROJECT_DEFINITION or DIM_EMPLOYEE)

3. NO RLS: Tables that don't need security joins
--------------------------------------------------------------------------------

================================================================================
*/

-- ============================================================================
-- SCRIPT EXECUTION
-- ============================================================================

PRINT '================================================================================';
PRINT 'FACT TABLES - VIEW DDL GENERATOR WITH ROW-LEVEL SECURITY';
PRINT '================================================================================';
PRINT 'Source Schema: ELT_ANALYTICS';
PRINT 'Target Schema: DATAMART_FACT';
PRINT 'Table Prefix:  FACT_';
PRINT 'View Prefix:   VW_';
PRINT '================================================================================';
PRINT '';

-- ============================================================================
-- MAIN CTE - Generate all view definitions with RLS configuration
-- ============================================================================

WITH RLSConfig AS (
    -- ========================================================================
    -- RLS CONFIGURATION TABLE
    -- ========================================================================
    -- TO ADD A NEW TABLE:
    -- 1. Add a new row with the table name and join configuration
    -- 2. For Direct Join: set BridgeTable to NULL, specify GeoColumn and SegColumn
    -- 3. For Bridge Join: set BridgeTable, BridgeAlias, JoinCol, PKCol, GeoCol, SegCol
    -- 4. For No RLS: set all columns to NULL except FactTableName
    -- ========================================================================
    SELECT * FROM (VALUES
        -- ====================================================================
        -- DIRECT JOIN TABLES (fact table has GEO and SEG columns directly)
        -- ====================================================================
        -- Format: (TableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
        ('FACT_PROJECT_REVENUE_LINES',  NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_PROJECT_COST_LINES',     NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_REV_BILL_AR_AGG',        NULL, NULL, NULL, NULL, 'OFFICE',            'TEAM'),
        ('FACT_AR_ERP_AGING',           NULL, NULL, NULL, NULL, 'GL_OFFICE_CODE',    'GL_TEAM_CODE'),
        ('FACT_AR_AGING_INVOICE',       NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',    'WC_TEAM_CODE'),
        ('FACT_UTILIZATION',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WAVG_FTE_MONTH_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WIP_ERP_AGING',          NULL, NULL, NULL, NULL, 'PROJECT_GL_OFFICE', 'PROJECT_GL_TEAM'),
        
        -- ====================================================================
        -- BRIDGE JOIN TABLES (via DIM_PROJECT_DEFINITION)
        -- ====================================================================
        ('FACT_PROJECT_COMMITMENTS',    'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENDITURES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENSE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_BUDGET_LINES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECTS_PROFITABILITY', 'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        
        -- ====================================================================
        -- BRIDGE JOIN TABLES (via DIM_EMPLOYEE)
        -- ====================================================================
        ('FACT_OTL_SUMMARY',            'DIM_EMPLOYEE', 'emp', 'RESOURCE_ID',  'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        ('FACT_PROJ_TIMECARD',          'DIM_EMPLOYEE', 'emp', 'ASSOC_ID',     'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        
        -- ====================================================================
        -- NO RLS TABLES (no security joins needed)
        -- ====================================================================
        ('FACT_WRKNG_DAYS_MONTH_AGG',   NULL, NULL, NULL, NULL, NULL, NULL)
        
    ) AS RLS(FactTableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
),
FilteredTables AS (
    -- Get all FACT tables from source schema
    SELECT 
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        t.object_id AS ObjectId
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'FACT_%'
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
    -- Build column list with fact. prefix for each table
    SELECT 
        ft.TableName,
        ft.ObjectId,
        STRING_AGG(
            'fact.[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
            ', '
        ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList
    FROM FilteredTables ft
    INNER JOIN sys.columns c ON ft.ObjectId = c.object_id
    GROUP BY ft.TableName, ft.ObjectId
),
TablesWithRLS AS (
    -- Join tables with RLS configuration
    SELECT 
        tc.TableName,
        'VW_' + tc.TableName AS ViewName,
        tc.ColumnList,
        r.BridgeTable,
        r.BridgeAlias,
        r.JoinColumn,
        r.PKColumn,
        r.GeoColumn,
        r.SegColumn,
        CASE WHEN r.FactTableName IS NULL THEN 0 ELSE 1 END AS HasRLSConfig
    FROM TableColumns tc
    LEFT JOIN RLSConfig r 
        ON tc.TableName COLLATE Latin1_General_100_BIN2_UTF8 = r.FactTableName COLLATE Latin1_General_100_BIN2_UTF8
),
ViewDefinitions AS (
    -- Generate complete DDL for each view
    SELECT 
        TableName,
        ViewName,
        ColumnList,
        HasRLSConfig,
        BridgeTable,
        GeoColumn,
        SegColumn,
        -- Determine RLS status for comments
        CASE 
            WHEN HasRLSConfig = 0 THEN 'NO CONFIG - Review Required'
            WHEN GeoColumn IS NULL AND SegColumn IS NULL THEN 'No RLS Joins'
            WHEN BridgeTable IS NOT NULL THEN 'Bridge via ' + BridgeTable
            ELSE 'Direct Join'
        END AS RLSStatus,
        -- Build the JOIN clause
        CASE 
            -- No config found
            WHEN HasRLSConfig = 0 THEN ''
            -- No RLS needed
            WHEN GeoColumn IS NULL AND SegColumn IS NULL THEN ''
            -- Has RLS config
            ELSE 
                -- Bridge table join (if needed)
                CASE 
                    WHEN BridgeTable IS NOT NULL THEN
                        'INNER JOIN [ELT_ANALYTICS].[' + BridgeTable + '] ' + BridgeAlias + 
                        ' ON fact.[' + JoinColumn + '] = ' + BridgeAlias + '.[' + PKColumn + ']' + CHAR(13) + CHAR(10)
                    ELSE ''
                END +
                -- GEO security join
                CASE 
                    WHEN GeoColumn IS NOT NULL THEN
                        'INNER JOIN [ELT_ANALYTICS].[WTWSecurityGEO] GEO ON ' +
                        CASE 
                            WHEN BridgeTable IS NOT NULL THEN BridgeAlias + '.[' + GeoColumn + ']'
                            ELSE 'fact.[' + GeoColumn + ']'
                        END + ' = GEO.GeoKey' + CHAR(13) + CHAR(10)
                    ELSE ''
                END +
                -- SEG security join
                CASE 
                    WHEN SegColumn IS NOT NULL THEN
                        'INNER JOIN [ELT_ANALYTICS].[WTWSecuritySEG] TEAM ON ' +
                        CASE 
                            WHEN BridgeTable IS NOT NULL THEN BridgeAlias + '.[' + SegColumn + ']'
                            ELSE 'fact.[' + SegColumn + ']'
                        END + ' = TEAM.SegKey' + CHAR(13) + CHAR(10)
                    ELSE ''
                END
        END AS JoinClause
    FROM TablesWithRLS
),
FinalDDL AS (
    -- Assemble complete DDL script
    SELECT 
        TableName,
        ViewName,
        RLSStatus,
        '-- ============================================================================' + CHAR(13) + CHAR(10) +
        '-- VIEW: ' + ViewName + CHAR(13) + CHAR(10) +
        '-- SOURCE: ELT_ANALYTICS.' + TableName + CHAR(13) + CHAR(10) +
        '-- RLS: ' + RLSStatus + CHAR(13) + CHAR(10) +
        '-- ============================================================================' + CHAR(13) + CHAR(10) +
        CHAR(13) + CHAR(10) +
        'DROP VIEW IF EXISTS [DATAMART_FACT].[' + ViewName + '];' + CHAR(13) + CHAR(10) +
        'GO' + CHAR(13) + CHAR(10) +
        CHAR(13) + CHAR(10) +
        'CREATE VIEW [DATAMART_FACT].[' + ViewName + ']' + CHAR(13) + CHAR(10) +
        'AS' + CHAR(13) + CHAR(10) +
        'SELECT ' + ColumnList + CHAR(13) + CHAR(10) +
        'FROM [ELT_ANALYTICS].[' + TableName + '] fact' + CHAR(13) + CHAR(10) +
        JoinClause +
        ';' + CHAR(13) + CHAR(10) +
        'GO' + CHAR(13) + CHAR(10) +
        CHAR(13) + CHAR(10) AS DDLScript
    FROM ViewDefinitions
)
-- Store results in temp table for output
SELECT 
    TableName,
    ViewName,
    RLSStatus,
    DDLScript
INTO #FactViewDDL
FROM FinalDDL;

-- ============================================================================
-- DISPLAY TABLES TO PROCESS
-- ============================================================================

PRINT '=== TABLES TO PROCESS ===';
PRINT '';

SELECT TableName, ViewName, RLSStatus FROM #FactViewDDL ORDER BY TableName;

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
PRINT 'IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = ''DATAMART_FACT'')';
PRINT 'BEGIN';
PRINT '    EXEC(''CREATE SCHEMA [DATAMART_FACT]'');';
PRINT 'END;';
PRINT 'GO';
PRINT '';
PRINT '-- ============================================================================';
PRINT '-- STEP 2: CREATE FACT VIEWS WITH ROW-LEVEL SECURITY';
PRINT '-- ============================================================================';
PRINT '';

-- ============================================================================
-- OUTPUT: VIEW DDL STATEMENTS
-- ============================================================================

SELECT DDLScript FROM #FactViewDDL ORDER BY TableName;

-- ============================================================================
-- SUMMARY
-- ============================================================================

PRINT '';
PRINT '================================================================================';
PRINT '-- GENERATION COMPLETE - RLS SUMMARY';
PRINT '================================================================================';

SELECT 
    RLSStatus,
    COUNT(*) AS TableCount
FROM #FactViewDDL 
GROUP BY RLSStatus
ORDER BY RLSStatus;

SELECT 
    'Total Views Generated: ' + CAST(COUNT(*) AS VARCHAR(10)) AS Summary
FROM #FactViewDDL;

PRINT '';
PRINT '-- IMPORTANT: Review tables marked "NO CONFIG - Review Required"';
PRINT '-- These tables were found but have no RLS configuration defined.';
PRINT '-- Add them to the RLSConfig CTE if they need security joins.';
PRINT '';
PRINT '-- Copy the DDL statements above and execute in your target environment';
PRINT '================================================================================';

-- Cleanup
DROP TABLE IF EXISTS #FactViewDDL;

/*
================================================================================
HOW TO ADD NEW TABLES TO RLS CONFIGURATION
================================================================================

1. DIRECT JOIN (table has GEO and SEG columns directly):
   Add a row in the RLSConfig CTE VALUES:
   ('FACT_NEW_TABLE', NULL, NULL, NULL, NULL, 'GEO_COLUMN_NAME', 'SEG_COLUMN_NAME'),

2. BRIDGE JOIN via DIM_PROJECT_DEFINITION:
   ('FACT_NEW_TABLE', 'DIM_PROJECT_DEFINITION', 'Proj', 'FACT_JOIN_COL', 'DIM_PK_COL', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),

3. BRIDGE JOIN via DIM_EMPLOYEE:
   ('FACT_NEW_TABLE', 'DIM_EMPLOYEE', 'emp', 'FACT_JOIN_COL', 'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),

4. NO RLS (no security joins needed):
   ('FACT_NEW_TABLE', NULL, NULL, NULL, NULL, NULL, NULL),

================================================================================
*/
