/*
================================================================================
FACT TABLES - VIEW DDL GENERATOR WITH ROW-LEVEL SECURITY
(FABRIC WAREHOUSE COMPATIBLE)
================================================================================
Purpose: Generate and optionally execute CREATE VIEW statements for FACT_ tables
         with Row-Level Security joins

Compatibility: Microsoft Fabric Warehouse (SQL Analytics Endpoint)
================================================================================

HOW TO USE:
--------------------------------------------------------------------------------
1. PREVIEW MODE: Run Section 1 and Section 2 to validate DDL before execution
2. EXECUTE MODE: Run Section 3 to get complete DDL script, then copy & execute
--------------------------------------------------------------------------------

CONFIGURATION - Edit these values by search/replace:
--------------------------------------------------------------------------------
Source Schema:  ELT_ANALYTICS         (search: ELT_ANALYTICS)
Target Schema:  DATAMART_FACT         (search: DATAMART_FACT)
Table Prefix:   FACT_                 (search: FACT_)
View Prefix:    VW_                   (search: VW_)
--------------------------------------------------------------------------------
*/

-- ============================================================================
-- SECTION 1: PREVIEW - Tables to be processed with RLS Status
-- ============================================================================
-- Run this to see which tables will have views created and their RLS config

SELECT 
    'PREVIEW' AS Mode,
    sub.TableName,
    'VW_' + sub.TableName AS ViewName,
    'DATAMART_FACT' AS TargetSchema,
    CASE 
        WHEN rls.FactTableName IS NULL THEN '** NO CONFIG - ADD TO RLS **'
        WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN 'No RLS Joins'
        WHEN rls.BridgeTable IS NOT NULL THEN 'Bridge: ' + rls.BridgeTable
        ELSE 'Direct Join'
    END AS RLSStatus,
    COALESCE(rls.GeoColumn, '-') AS GeoColumn,
    COALESCE(rls.SegColumn, '-') AS SegColumn
FROM (
    SELECT CONVERT(VARCHAR(8000), t.name) AS TableName
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'FACT_%'
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
) sub
LEFT JOIN (
    -- ========================================================================
    -- RLS CONFIGURATION TABLE
    -- ========================================================================
    SELECT * FROM (VALUES
        -- DIRECT JOIN TABLES
        ('FACT_PROJECT_REVENUE_LINES',  NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_PROJECT_COST_LINES',     NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_REV_BILL_AR_AGG',        NULL, NULL, NULL, NULL, 'OFFICE',            'TEAM'),
        ('FACT_AR_ERP_AGING',           NULL, NULL, NULL, NULL, 'GL_OFFICE_CODE',    'GL_TEAM_CODE'),
        ('FACT_AR_AGING_INVOICE',       NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',    'WC_TEAM_CODE'),
        ('FACT_UTILIZATION',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WAVG_FTE_MONTH_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WIP_ERP_AGING',          NULL, NULL, NULL, NULL, 'PROJECT_GL_OFFICE', 'PROJECT_GL_TEAM'),
        -- BRIDGE via DIM_PROJECT_DEFINITION
        ('FACT_PROJECT_COMMITMENTS',    'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENDITURES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENSE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_BUDGET_LINES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECTS_PROFITABILITY', 'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        -- BRIDGE via DIM_EMPLOYEE
        ('FACT_OTL_SUMMARY',            'DIM_EMPLOYEE', 'emp', 'RESOURCE_ID',  'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        ('FACT_PROJ_TIMECARD',          'DIM_EMPLOYEE', 'emp', 'ASSOC_ID',     'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        -- NO RLS
        ('FACT_WRKNG_DAYS_MONTH_AGG',   NULL, NULL, NULL, NULL, NULL, NULL)
    ) AS R(FactTableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
) rls ON sub.TableName COLLATE Latin1_General_100_BIN2_UTF8 = rls.FactTableName COLLATE Latin1_General_100_BIN2_UTF8
ORDER BY sub.TableName;

-- ============================================================================
-- SECTION 2: PREVIEW - Individual DDL Statements (for validation)
-- ============================================================================
-- Run this to see each DDL statement separately with RLS joins

SELECT 
    sub.TableName,
    'VW_' + sub.TableName AS ViewName,
    CASE 
        WHEN rls.FactTableName IS NULL THEN '** NO CONFIG **'
        WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN 'No RLS'
        WHEN rls.BridgeTable IS NOT NULL THEN 'Bridge: ' + rls.BridgeTable
        ELSE 'Direct'
    END AS RLSType,
    'DROP VIEW IF EXISTS [DATAMART_FACT].[VW_' + sub.TableName + '];' AS DropStatement,
    'CREATE VIEW [DATAMART_FACT].[VW_' + sub.TableName + '] AS SELECT ' + sub.ColumnList + 
    ' FROM [ELT_ANALYTICS].[' + sub.TableName + '] fact' +
    CASE 
        WHEN rls.FactTableName IS NULL THEN ''
        WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN ''
        ELSE 
            COALESCE(
                CASE WHEN rls.BridgeTable IS NOT NULL 
                    THEN ' INNER JOIN [ELT_ANALYTICS].[' + rls.BridgeTable + '] ' + rls.BridgeAlias + 
                         ' ON fact.[' + rls.JoinColumn + '] = ' + rls.BridgeAlias + '.[' + rls.PKColumn + ']'
                    ELSE '' 
                END, '') +
            COALESCE(
                CASE WHEN rls.GeoColumn IS NOT NULL 
                    THEN ' INNER JOIN [ELT_ANALYTICS].[WTWSecurityGEO] GEO ON ' +
                         CASE WHEN rls.BridgeTable IS NOT NULL 
                             THEN rls.BridgeAlias + '.[' + rls.GeoColumn + ']'
                             ELSE 'fact.[' + rls.GeoColumn + ']'
                         END + ' = GEO.GeoKey'
                    ELSE '' 
                END, '') +
            COALESCE(
                CASE WHEN rls.SegColumn IS NOT NULL 
                    THEN ' INNER JOIN [ELT_ANALYTICS].[WTWSecuritySEG] TEAM ON ' +
                         CASE WHEN rls.BridgeTable IS NOT NULL 
                             THEN rls.BridgeAlias + '.[' + rls.SegColumn + ']'
                             ELSE 'fact.[' + rls.SegColumn + ']'
                         END + ' = TEAM.SegKey'
                    ELSE '' 
                END, '')
    END + ';' AS CreateStatement
FROM (
    SELECT 
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        STRING_AGG(
            'fact.[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
            ', '
        ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'FACT_%'
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
LEFT JOIN (
    SELECT * FROM (VALUES
        -- DIRECT JOIN
        ('FACT_PROJECT_REVENUE_LINES',  NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_PROJECT_COST_LINES',     NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_REV_BILL_AR_AGG',        NULL, NULL, NULL, NULL, 'OFFICE',            'TEAM'),
        ('FACT_AR_ERP_AGING',           NULL, NULL, NULL, NULL, 'GL_OFFICE_CODE',    'GL_TEAM_CODE'),
        ('FACT_AR_AGING_INVOICE',       NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',    'WC_TEAM_CODE'),
        ('FACT_UTILIZATION',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WAVG_FTE_MONTH_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WIP_ERP_AGING',          NULL, NULL, NULL, NULL, 'PROJECT_GL_OFFICE', 'PROJECT_GL_TEAM'),
        -- BRIDGE via DIM_PROJECT_DEFINITION
        ('FACT_PROJECT_COMMITMENTS',    'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENDITURES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENSE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_BUDGET_LINES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECTS_PROFITABILITY', 'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        -- BRIDGE via DIM_EMPLOYEE
        ('FACT_OTL_SUMMARY',            'DIM_EMPLOYEE', 'emp', 'RESOURCE_ID',  'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        ('FACT_PROJ_TIMECARD',          'DIM_EMPLOYEE', 'emp', 'ASSOC_ID',     'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        -- NO RLS
        ('FACT_WRKNG_DAYS_MONTH_AGG',   NULL, NULL, NULL, NULL, NULL, NULL)
    ) AS R(FactTableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
) rls ON sub.TableName COLLATE Latin1_General_100_BIN2_UTF8 = rls.FactTableName COLLATE Latin1_General_100_BIN2_UTF8
ORDER BY sub.TableName;


-- ****************************************************************************
-- ****************************************************************************
-- EXECUTE MODE - Run section below, then copy output and execute it
-- ****************************************************************************
-- ****************************************************************************

-- ============================================================================
-- SECTION 3: EXECUTE - Generate Complete DDL Script
-- ============================================================================
-- Run this query, then copy the DDL_Script column output and execute it
-- The output contains all DROP + CREATE statements with RLS joins

/*
SELECT 
    '-- ============================================================================
-- AUTO-GENERATED FACT VIEWS DDL WITH ROW-LEVEL SECURITY
-- Generated: ' + CONVERT(VARCHAR(20), GETDATE(), 120) + '
-- Schema: DATAMART_FACT
-- ============================================================================

-- Create schema if not exists
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = ''DATAMART_FACT'')
    EXEC(''CREATE SCHEMA [DATAMART_FACT]'');

' + STRING_AGG(
        '-- View: VW_' + sub.TableName + ' | RLS: ' + 
        CASE 
            WHEN rls.FactTableName IS NULL THEN 'NO CONFIG'
            WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN 'None'
            WHEN rls.BridgeTable IS NOT NULL THEN 'Bridge(' + rls.BridgeTable + ')'
            ELSE 'Direct'
        END + '
DROP VIEW IF EXISTS [DATAMART_FACT].[VW_' + sub.TableName + '];
GO
CREATE VIEW [DATAMART_FACT].[VW_' + sub.TableName + '] AS 
SELECT ' + sub.ColumnList + ' 
FROM [ELT_ANALYTICS].[' + sub.TableName + '] fact' +
        CASE 
            WHEN rls.FactTableName IS NULL THEN ''
            WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN ''
            ELSE 
                COALESCE(
                    CASE WHEN rls.BridgeTable IS NOT NULL 
                        THEN '
INNER JOIN [ELT_ANALYTICS].[' + rls.BridgeTable + '] ' + rls.BridgeAlias + ' ON fact.[' + rls.JoinColumn + '] = ' + rls.BridgeAlias + '.[' + rls.PKColumn + ']'
                        ELSE '' 
                    END, '') +
                COALESCE(
                    CASE WHEN rls.GeoColumn IS NOT NULL 
                        THEN '
INNER JOIN [ELT_ANALYTICS].[WTWSecurityGEO] GEO ON ' +
                             CASE WHEN rls.BridgeTable IS NOT NULL 
                                 THEN rls.BridgeAlias + '.[' + rls.GeoColumn + ']'
                                 ELSE 'fact.[' + rls.GeoColumn + ']'
                             END + ' = GEO.GeoKey'
                        ELSE '' 
                    END, '') +
                COALESCE(
                    CASE WHEN rls.SegColumn IS NOT NULL 
                        THEN '
INNER JOIN [ELT_ANALYTICS].[WTWSecuritySEG] TEAM ON ' +
                             CASE WHEN rls.BridgeTable IS NOT NULL 
                                 THEN rls.BridgeAlias + '.[' + rls.SegColumn + ']'
                                 ELSE 'fact.[' + rls.SegColumn + ']'
                             END + ' = TEAM.SegKey'
                        ELSE '' 
                    END, '')
        END + ';
GO
',
        '
'
    ) AS DDL_Script
FROM (
    SELECT 
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        STRING_AGG(
            'fact.[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
            ', '
        ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'FACT_%'
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
LEFT JOIN (
    SELECT * FROM (VALUES
        -- DIRECT JOIN
        ('FACT_PROJECT_REVENUE_LINES',  NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_PROJECT_COST_LINES',     NULL, NULL, NULL, NULL, 'GEO_KEY',           'SEGMENT_KEY'),
        ('FACT_REV_BILL_AR_AGG',        NULL, NULL, NULL, NULL, 'OFFICE',            'TEAM'),
        ('FACT_AR_ERP_AGING',           NULL, NULL, NULL, NULL, 'GL_OFFICE_CODE',    'GL_TEAM_CODE'),
        ('FACT_AR_AGING_INVOICE',       NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',    'WC_TEAM_CODE'),
        ('FACT_UTILIZATION',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WAVG_FTE_MONTH_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',       'TEAM_CODE'),
        ('FACT_WIP_ERP_AGING',          NULL, NULL, NULL, NULL, 'PROJECT_GL_OFFICE', 'PROJECT_GL_TEAM'),
        -- BRIDGE via DIM_PROJECT_DEFINITION
        ('FACT_PROJECT_COMMITMENTS',    'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENDITURES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENSE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_BUDGET_LINES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECTS_PROFITABILITY', 'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        -- BRIDGE via DIM_EMPLOYEE
        ('FACT_OTL_SUMMARY',            'DIM_EMPLOYEE', 'emp', 'RESOURCE_ID',  'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        ('FACT_PROJ_TIMECARD',          'DIM_EMPLOYEE', 'emp', 'ASSOC_ID',     'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        -- NO RLS
        ('FACT_WRKNG_DAYS_MONTH_AGG',   NULL, NULL, NULL, NULL, NULL, NULL)
    ) AS R(FactTableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
) rls ON sub.TableName COLLATE Latin1_General_100_BIN2_UTF8 = rls.FactTableName COLLATE Latin1_General_100_BIN2_UTF8;
*/

-- ============================================================================
-- SECTION 4: VERIFY - Check created views
-- ============================================================================
-- Run this after execution to verify views were created

/*
SELECT 
    s.name AS SchemaName,
    v.name AS ViewName,
    v.create_date AS CreatedDate
FROM sys.views v
INNER JOIN sys.schemas s ON v.schema_id = s.schema_id
WHERE s.name = 'DATAMART_FACT'
ORDER BY v.name;
*/


/*
================================================================================
HOW TO ADD NEW TABLES TO RLS CONFIGURATION
================================================================================

Find ALL VALUES sections in this script (Sections 1, 2, and 3) and add the same
row to each:

PATTERNS:
--------------------------------------------------------------------------------

1. DIRECT JOIN (fact table has GEO and SEG columns directly):
   ('FACT_NEW_TABLE', NULL, NULL, NULL, NULL, 'GEO_COLUMN', 'SEG_COLUMN'),

2. BRIDGE JOIN via DIM_PROJECT_DEFINITION:
   ('FACT_NEW_TABLE', 'DIM_PROJECT_DEFINITION', 'Proj', 'FACT_FK_COL', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),

3. BRIDGE JOIN via DIM_EMPLOYEE:
   ('FACT_NEW_TABLE', 'DIM_EMPLOYEE', 'emp', 'FACT_FK_COL', 'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),

4. NO RLS (no security joins needed):
   ('FACT_NEW_TABLE', NULL, NULL, NULL, NULL, NULL, NULL),

================================================================================
*/
