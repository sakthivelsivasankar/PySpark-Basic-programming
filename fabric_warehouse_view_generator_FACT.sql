/*
================================================================================
FACT TABLES - VIEW DDL GENERATOR WITH ROW-LEVEL SECURITY
(FABRIC WAREHOUSE COMPATIBLE)
================================================================================
Purpose: Generate CREATE VIEW statements for FACT_ tables with RLS security joins

Compatibility: Microsoft Fabric Warehouse (SQL Analytics Endpoint)
================================================================================

HOW TO USE:
--------------------------------------------------------------------------------
1. PREVIEW MODE: Run Section 1 to see tables with RLS status
2. EXECUTE MODE: Run Section 2, copy all rows from DDL column, execute
--------------------------------------------------------------------------------

CONFIGURATION - Edit these values by search/replace:
--------------------------------------------------------------------------------
Source Schema:  ELT_ANALYTICS         (search: ELT_ANALYTICS)
Target Schema:  DATAMART_FACT         (search: DATAMART_FACT)
Table Prefix:   FACT_                 (search: FACT_)
View Prefix:    VW_                   (search: VW_)
Security GEO:   WTWSecurityGEOSec     (search: WTWSecurityGEOSec)
Security SEG:   WTWSecuritySEGSec     (search: WTWSecuritySEGSec)
--------------------------------------------------------------------------------

IGNORE TABLE FILTERS:
--------------------------------------------------------------------------------
Table name CONTAINS (keyword filter):
  - _TMP
  - _STAGE
  - TEMP, temp, TEST, test, BACKUP, backup, Archive, ARCHIVE
  - STG, DUMMY, _BKP, _OLS, _CLS, _VY, _TW, _T, _1, _2

Specific tables to IGNORE:
  - FACT_CUST_LOC_USE_PERSIST_REV
  - FACT_HR_INTERIM_ROSTER_STAGE
  - FACT_PARTY_CONTACT_PERSIST_REV
  - FACT_WEVT_EQ_TMP
  - FACT_WEVT_SUP_EQ_TMP
  - FACT_WRKFC_EVT_EQ_TMP
  - FACT_WRKFC_EVT_MONTH_EQ_TMP
  - FACT_WRKFC_EVENT_AGE
  - FACT_WRKFC_EVENT_POW
--------------------------------------------------------------------------------
*/

-- ============================================================================
-- SECTION 1: PREVIEW - Tables with RLS Status
-- ============================================================================

SELECT 
    ROW_NUMBER() OVER (ORDER BY sub.TableName) AS RowNum,
    sub.TableName,
    'VW_' + sub.TableName AS ViewName,
    CASE 
        WHEN rls.FactTableName IS NULL THEN '** NO CONFIG **'
        WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN 'No RLS'
        WHEN rls.BridgeTable IS NOT NULL THEN 'Bridge: ' + rls.BridgeTable
        ELSE 'Direct Join'
    END AS RLSStatus,
    COALESCE(rls.GeoColumn, '-') AS GeoCol,
    COALESCE(rls.SegColumn, '-') AS SegCol
FROM (
    SELECT CONVERT(VARCHAR(8000), t.name) AS TableName
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'FACT_%'
      -- Keyword filters (CONTAINS)
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_TMP%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_STAGE%'
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
      -- Specific tables to IGNORE
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT IN (
          'FACT_CUST_LOC_USE_PERSIST_REV',
          'FACT_HR_INTERIM_ROSTER_STAGE',
          'FACT_PARTY_CONTACT_PERSIST_REV',
          'FACT_WEVT_EQ_TMP',
          'FACT_WEVT_SUP_EQ_TMP',
          'FACT_WRKFC_EVT_EQ_TMP',
          'FACT_WRKFC_EVT_MONTH_EQ_TMP',
          'FACT_WRKFC_EVENT_AGE',
          'FACT_WRKFC_EVENT_POW'
      )
) sub
LEFT JOIN (
    SELECT * FROM (VALUES
        -- ===== DIRECT JOIN - Financial/Revenue Tables =====
        ('FACT_PROJECT_REVENUE_LINES',  NULL, NULL, NULL, NULL, 'GEO_KEY',              'SEGMENT_KEY'),
        ('FACT_PROJECT_COST_LINES',     NULL, NULL, NULL, NULL, 'GEO_KEY',              'SEGMENT_KEY'),
        ('FACT_REV_BILL_AR_AGG',        NULL, NULL, NULL, NULL, 'OFFICE',               'TEAM'),
        ('FACT_REV_BILL_AR_AGG_ITD',    NULL, NULL, NULL, NULL, 'OFFICE',               'TEAM'),
        
        -- ===== DIRECT JOIN - AR Tables =====
        ('FACT_AR_ERP_AGING',           NULL, NULL, NULL, NULL, 'GL_OFFICE_CODE',       'GL_TEAM_CODE'),
        ('FACT_AR_AGING_INVOICE',       NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
        ('FACT_AR_XACT',                NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
        ('FACT_AR_XACT_REV',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
        
        -- ===== DIRECT JOIN - Utilization/FTE Tables =====
        ('FACT_UTILIZATION',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
        ('FACT_WAVG_FTE_MONTH_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
        ('FACT_WAVG_FTE_DAILY_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
        ('FACT_WIP_ERP_AGING',          NULL, NULL, NULL, NULL, 'PROJECT_GL_OFFICE_ID', 'PROJECT_GL_TEAM_ID'),
        
        -- ===== DIRECT JOIN - Employee/HR Tables =====
        ('FACT_CUR_EMPLOYEE_RATE',      NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
        ('FACT_PA_BILL_RATES',          NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
        ('FACT_HR_INTERIM_ROSTER',      NULL, NULL, NULL, NULL, 'COSTING_OFFICE_CODE',  'TEAM_CODE'),
        ('FACT_HR_INTERIM_ROSTER_MONTH',NULL, NULL, NULL, NULL, 'COSTING_OFFICE_CODE',  'TEAM_CODE'),
        ('FACT_HR_INTERIM_SNAPSHOT',    NULL, NULL, NULL, NULL, 'COSTING_OFFICE_CODE',  'TEAM_CODE'),
        
        -- ===== DIRECT JOIN - Workforce Event Tables =====
        ('FACT_WEVT_PERSIST',           NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
        ('FACT_WRKFC_EVENT_MERGE',      NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
        ('FACT_WRKFC_EVENT_MONTH',      NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
        ('FACT_WRKFC_EVT_ASG_PERSIST',  NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
        
        -- ===== BRIDGE JOIN - via DIM_PROJECT_DEFINITION =====
        ('FACT_PROJECT_COMMITMENTS',    'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENDITURES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_EXPENSE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_BUDGET_LINES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECTS_PROFITABILITY', 'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_BUDGET',         'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_CC_COST',        'DIM_PROJECT_DEFINITION', 'Proj', 'IC_PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        ('FACT_PROJECT_INVOICE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
        
        -- ===== BRIDGE JOIN - via DIM_EMPLOYEE =====
        ('FACT_OTL_SUMMARY',            'DIM_EMPLOYEE', 'emp', 'RESOURCE_ID',  'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        ('FACT_PROJ_TIMECARD',          'DIM_EMPLOYEE', 'emp', 'ASSOC_ID',     'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
        
        -- ===== NO RLS - Working Days (no GEO/SEG columns) =====
        ('FACT_WRKNG_DAYS_MONTH_AGG',   NULL, NULL, NULL, NULL, NULL, NULL),
        
        -- ===== NO RLS - Persist tables without GEO/SEG columns =====
        ('FACT_CUST_LOC_USE_PERSIST',   NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_DMN_WEVT_TYP_PERSIST',   NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_PARTY_CONTACT_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_FTE_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_GRT_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_HDC_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_PERF_PERSIST', NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_POW_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_PSN_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_PTYP_PERSIST', NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_SAL_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_EVT_SUP_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_WRKFC_SUPV_STATUS_PERSIST', NULL, NULL, NULL, NULL, NULL, NULL),
        
        -- ===== NO RLS - Revenue Headers (uses PROJECT_KEY not PROJECT_ID) =====
        ('FACT_PROJECT_REVENUE_HEADERS', NULL, NULL, NULL, NULL, NULL, NULL),
        ('FACT_PROJ_GL_RECNCLIATION',   NULL, NULL, NULL, NULL, NULL, NULL)
    ) AS R(FactTableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
) rls ON sub.TableName COLLATE Latin1_General_100_BIN2_UTF8 = rls.FactTableName COLLATE Latin1_General_100_BIN2_UTF8
ORDER BY sub.TableName;


-- ============================================================================
-- SECTION 2: EXECUTE - DDL Statements (copy all rows and execute)
-- ============================================================================
-- Instructions:
-- 1. Run this query
-- 2. Select all rows in the DDL column  
-- 3. Copy to a new query window
-- 4. Execute the copied DDL

-- Schema creation
SELECT 0 AS Seq, 'SCHEMA' AS Type, 'Schema' AS ViewName, 'None' AS RLS,
'IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = ''DATAMART_FACT'') EXEC(''CREATE SCHEMA [DATAMART_FACT]'');
GO' AS DDL

UNION ALL

-- All view DDL statements with GO separators and RLS joins
SELECT 
    sub.Seq,
    'VIEW' AS Type,
    sub.ViewName,
    sub.RLSStatus AS RLS,
    'DROP VIEW IF EXISTS [DATAMART_FACT].[' + sub.ViewName + '];
GO
CREATE VIEW [DATAMART_FACT].[' + sub.ViewName + '] AS SELECT ' + sub.ColumnList + 
    ' FROM [ELT_ANALYTICS].[' + sub.TableName + '] fact' + sub.JoinClause + ';
GO' AS DDL
FROM (
    SELECT 
        ROW_NUMBER() OVER (ORDER BY CONVERT(VARCHAR(8000), t.name)) AS Seq,
        CONVERT(VARCHAR(8000), t.name) AS TableName,
        'VW_' + CONVERT(VARCHAR(8000), t.name) AS ViewName,
        STRING_AGG(
            'fact.[' + CONVERT(VARCHAR(8000), c.name) COLLATE Latin1_General_100_BIN2_UTF8 + ']',
            ', '
        ) WITHIN GROUP (ORDER BY c.column_id) AS ColumnList,
        CASE 
            WHEN rls.FactTableName IS NULL THEN 'NO CONFIG'
            WHEN rls.GeoColumn IS NULL AND rls.SegColumn IS NULL THEN 'None'
            WHEN rls.BridgeTable IS NOT NULL THEN 'Bridge'
            ELSE 'Direct'
        END AS RLSStatus,
        -- Build JOIN clause
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
                        THEN ' INNER JOIN [ELT_ANALYTICS].[WTWSecurityGEOSec] GEO ON ' +
                             CASE WHEN rls.BridgeTable IS NOT NULL 
                                 THEN rls.BridgeAlias + '.[' + rls.GeoColumn + ']'
                                 ELSE 'fact.[' + rls.GeoColumn + ']'
                             END + ' = GEO.GeoKey'
                        ELSE '' 
                    END, '') +
                COALESCE(
                    CASE WHEN rls.SegColumn IS NOT NULL 
                        THEN ' INNER JOIN [ELT_ANALYTICS].[WTWSecuritySEGSec] TEAM ON ' +
                             CASE WHEN rls.BridgeTable IS NOT NULL 
                                 THEN rls.BridgeAlias + '.[' + rls.SegColumn + ']'
                                 ELSE 'fact.[' + rls.SegColumn + ']'
                             END + ' = TEAM.SegKey'
                        ELSE '' 
                    END, '')
        END AS JoinClause
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    LEFT JOIN (
        SELECT * FROM (VALUES
            -- ===== DIRECT JOIN - Financial/Revenue Tables =====
            ('FACT_PROJECT_REVENUE_LINES',  NULL, NULL, NULL, NULL, 'GEO_KEY',              'SEGMENT_KEY'),
            ('FACT_PROJECT_COST_LINES',     NULL, NULL, NULL, NULL, 'GEO_KEY',              'SEGMENT_KEY'),
            ('FACT_REV_BILL_AR_AGG',        NULL, NULL, NULL, NULL, 'OFFICE',               'TEAM'),
            ('FACT_REV_BILL_AR_AGG_ITD',    NULL, NULL, NULL, NULL, 'OFFICE',               'TEAM'),
            
            -- ===== DIRECT JOIN - AR Tables =====
            ('FACT_AR_ERP_AGING',           NULL, NULL, NULL, NULL, 'GL_OFFICE_CODE',       'GL_TEAM_CODE'),
            ('FACT_AR_AGING_INVOICE',       NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
            ('FACT_AR_XACT',                NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
            ('FACT_AR_XACT_REV',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
            
            -- ===== DIRECT JOIN - Utilization/FTE Tables =====
            ('FACT_UTILIZATION',            NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
            ('FACT_WAVG_FTE_MONTH_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
            ('FACT_WAVG_FTE_DAILY_AGG',     NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
            ('FACT_WIP_ERP_AGING',          NULL, NULL, NULL, NULL, 'PROJECT_GL_OFFICE_ID', 'PROJECT_GL_TEAM_ID'),
            
            -- ===== DIRECT JOIN - Employee/HR Tables =====
            ('FACT_CUR_EMPLOYEE_RATE',      NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
            ('FACT_PA_BILL_RATES',          NULL, NULL, NULL, NULL, 'OFFICE_CODE',          'TEAM_CODE'),
            ('FACT_HR_INTERIM_ROSTER',      NULL, NULL, NULL, NULL, 'COSTING_OFFICE_CODE',  'TEAM_CODE'),
            ('FACT_HR_INTERIM_ROSTER_MONTH',NULL, NULL, NULL, NULL, 'COSTING_OFFICE_CODE',  'TEAM_CODE'),
            ('FACT_HR_INTERIM_SNAPSHOT',    NULL, NULL, NULL, NULL, 'COSTING_OFFICE_CODE',  'TEAM_CODE'),
            
            -- ===== DIRECT JOIN - Workforce Event Tables =====
            ('FACT_WEVT_PERSIST',           NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
            ('FACT_WRKFC_EVENT_MERGE',      NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
            ('FACT_WRKFC_EVENT_MONTH',      NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
            ('FACT_WRKFC_EVT_ASG_PERSIST',  NULL, NULL, NULL, NULL, 'WC_OFFICE_CODE',       'WC_TEAM_CODE'),
            
            -- ===== BRIDGE JOIN - via DIM_PROJECT_DEFINITION =====
            ('FACT_PROJECT_COMMITMENTS',    'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECT_EXPENDITURES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECT_EXPENSE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECT_BUDGET_LINES',   'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECTS_PROFITABILITY', 'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECT_BUDGET',         'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECT_CC_COST',        'DIM_PROJECT_DEFINITION', 'Proj', 'IC_PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            ('FACT_PROJECT_INVOICE_LINES',  'DIM_PROJECT_DEFINITION', 'Proj', 'PROJECT_ID', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),
            
            -- ===== BRIDGE JOIN - via DIM_EMPLOYEE =====
            ('FACT_OTL_SUMMARY',            'DIM_EMPLOYEE', 'emp', 'RESOURCE_ID',  'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
            ('FACT_PROJ_TIMECARD',          'DIM_EMPLOYEE', 'emp', 'ASSOC_ID',     'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),
            
            -- ===== NO RLS - Working Days (no GEO/SEG columns) =====
            ('FACT_WRKNG_DAYS_MONTH_AGG',   NULL, NULL, NULL, NULL, NULL, NULL),
            
            -- ===== NO RLS - Persist tables without GEO/SEG columns =====
            ('FACT_CUST_LOC_USE_PERSIST',   NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_DMN_WEVT_TYP_PERSIST',   NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_PARTY_CONTACT_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_FTE_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_GRT_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_HDC_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_PERF_PERSIST', NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_POW_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_PSN_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_PTYP_PERSIST', NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_SAL_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_EVT_SUP_PERSIST',  NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_WRKFC_SUPV_STATUS_PERSIST', NULL, NULL, NULL, NULL, NULL, NULL),
            
            -- ===== NO RLS - Revenue Headers (uses PROJECT_KEY not PROJECT_ID) =====
            ('FACT_PROJECT_REVENUE_HEADERS', NULL, NULL, NULL, NULL, NULL, NULL),
            ('FACT_PROJ_GL_RECNCLIATION',   NULL, NULL, NULL, NULL, NULL, NULL)
        ) AS R(FactTableName, BridgeTable, BridgeAlias, JoinColumn, PKColumn, GeoColumn, SegColumn)
    ) rls ON CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 = rls.FactTableName COLLATE Latin1_General_100_BIN2_UTF8
    WHERE CONVERT(VARCHAR(8000), s.name) COLLATE Latin1_General_100_BIN2_UTF8 = 'ELT_ANALYTICS'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 LIKE 'FACT_%'
      -- Keyword filters (CONTAINS)
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_TMP%'
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT LIKE '%_STAGE%'
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
      -- Specific tables to IGNORE
      AND CONVERT(VARCHAR(8000), t.name) COLLATE Latin1_General_100_BIN2_UTF8 NOT IN (
          'FACT_CUST_LOC_USE_PERSIST_REV',
          'FACT_HR_INTERIM_ROSTER_STAGE',
          'FACT_PARTY_CONTACT_PERSIST_REV',
          'FACT_WEVT_EQ_TMP',
          'FACT_WEVT_SUP_EQ_TMP',
          'FACT_WRKFC_EVT_EQ_TMP',
          'FACT_WRKFC_EVT_MONTH_EQ_TMP',
          'FACT_WRKFC_EVENT_AGE',
          'FACT_WRKFC_EVENT_POW'
      )
    GROUP BY t.name, rls.FactTableName, rls.BridgeTable, rls.BridgeAlias, rls.JoinColumn, rls.PKColumn, rls.GeoColumn, rls.SegColumn
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
WHERE s.name = 'DATAMART_FACT'
ORDER BY v.name;
*/


/*
================================================================================
HOW TO ADD NEW TABLES TO RLS CONFIGURATION
================================================================================

Find BOTH VALUES sections in this script (Section 1 and Section 2) and add:

1. DIRECT JOIN:
   ('FACT_NEW_TABLE', NULL, NULL, NULL, NULL, 'GEO_COL', 'SEG_COL'),

2. BRIDGE via DIM_PROJECT_DEFINITION:
   ('FACT_NEW_TABLE', 'DIM_PROJECT_DEFINITION', 'Proj', 'FK_COL', 'PROJECT_ID', 'WC_OFFICE_CODE', 'WC_TEAM_CODE'),

3. BRIDGE via DIM_EMPLOYEE:
   ('FACT_NEW_TABLE', 'DIM_EMPLOYEE', 'emp', 'FK_COL', 'EMPLOYEE_NUM', 'WC_SEGMENT3_OFFICE', 'WC_SEGMENT4_TEAM'),

4. NO RLS:
   ('FACT_NEW_TABLE', NULL, NULL, NULL, NULL, NULL, NULL),

================================================================================
*/
