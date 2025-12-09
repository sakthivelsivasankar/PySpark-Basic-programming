import pandas as pd
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re
import glob

def safe_str(value, default=''):
    """Safely convert value to string, handling NaN/None"""
    if pd.isna(value) or value is None:
        return default
    return str(value)

def safe_lower(value, default=''):
    """Safely convert value to lowercase string"""
    if pd.isna(value) or value is None:
        return default
    return str(value).lower()

class PowerBIDocumentationGenerator:
    def __init__(self, columns_df, measures_df, relationships_df, semantic_model_name, mapping_df=None):
        """Initialize with DataFrames and semantic model name
        
        Args:
            columns_df: DataFrame with columns metadata
            measures_df: DataFrame with measures metadata
            relationships_df: DataFrame with relationships metadata
            semantic_model_name: Name of the semantic model
            mapping_df: Optional DataFrame with Oracle to Power BI mapping
        """
        self.semantic_model_name = semantic_model_name
        
        # Clean the dataframes - remove rows with null Table or Column names
        self.columns_df = columns_df.copy()
        self.columns_df = self.columns_df[self.columns_df['Table'].notna() & self.columns_df['Column'].notna()]
        
        self.measures_df = measures_df.copy()
        
        self.relationships_df = relationships_df.copy()
        # Clean relationships - remove rows with null table/column references
        required_rel_cols = ['From Table', 'From Column', 'To Table', 'To Column']
        for col in required_rel_cols:
            if col in self.relationships_df.columns:
                self.relationships_df = self.relationships_df[self.relationships_df[col].notna()]
        
        self.mapping_df = mapping_df
        
        # Detect the measure name column (could be 'Measure', 'Name', 'Measure Name', etc.)
        self.measure_name_column = self._detect_measure_name_column()
        
        # Build physical table/column lookup cache for performance
        self._build_physical_mapping_cache()
        
        # Identify fact and dimension tables
        self.fact_tables = []
        self.dim_tables = []
        self._classify_tables()
    
    def _detect_measure_name_column(self):
        """Detect the column name used for measure names in the measures CSV"""
        # Priority order for measure name columns
        possible_names = ['Measure', 'Name', 'Measure Name', 'MeasureName', 'measure', 'name']
        for col_name in possible_names:
            if col_name in self.measures_df.columns:
                return col_name
        
        # If no match, return the first column that's not a known metadata column
        # IMPORTANT: Exclude 'Type' as it contains category info, not measure names
        exclude_cols = ['Table', 'Type', 'Description', 'DAX Expression', 'Is Hidden', 
                        'Format String', 'Display Folder', 'Expression', 'Data Type',
                        'Data Category', 'Is Key', 'Column Type', 'Summarize By']
        for col in self.measures_df.columns:
            if col not in exclude_cols:
                return col
        return 'Measure'  # Default fallback
    
    def _build_physical_mapping_cache(self):
        """Build a cache of physical table and column mappings for quick lookup"""
        self._physical_table_cache = {}
        self._physical_column_cache = {}
        
        for _, row in self.columns_df.iterrows():
            table_name = safe_str(row.get('Table', ''))
            column_name = safe_str(row.get('Column', ''))
            
            if not table_name:
                continue
            
            # Cache physical table name
            if table_name not in self._physical_table_cache:
                physical_table = self._extract_physical_table_name(row)
                self._physical_table_cache[table_name] = physical_table
            
            # Cache physical column name
            if column_name:
                cache_key = (table_name, column_name)
                physical_col = self._extract_physical_column_name(row, column_name)
                self._physical_column_cache[cache_key] = physical_col
    
    def _extract_physical_table_name(self, row):
        """Extract physical table name from a row"""
        # Try Source Query/Expression column first
        source_query = row.get('Source Query/Expression', '')
        if pd.notna(source_query) and str(source_query).strip():
            source_str = str(source_query).strip()
            
            # Pattern 1: Direct table name (no SQL keywords)
            if not any(keyword in source_str.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'JOIN']):
                cleaned = source_str.replace('[', '').replace(']', '').replace('"', '').replace("'", '').strip()
                if '.' in cleaned:
                    cleaned = cleaned.split('.')[-1]
                if cleaned:
                    return cleaned
            
            # Pattern 2: SQL Query with FROM clause
            source_upper = source_str.upper()
            if 'FROM' in source_upper:
                try:
                    from_idx = source_upper.find('FROM')
                    after_from = source_str[from_idx + 4:].strip()
                    table_part = after_from.split()[0] if after_from.split() else ''
                    table_part = table_part.replace('[', '').replace(']', '').replace('"', '').replace("'", '').replace(',', '').strip()
                    if '.' in table_part:
                        table_part = table_part.split('.')[-1]
                    if table_part:
                        return table_part
                except:
                    pass
        
        # Fallback: Source Column field - extract table name part
        source = row.get('Source Column', '')
        if pd.notna(source) and str(source).strip():
            source_str = str(source).strip()
            # Pattern: [TableName].[ColumnName] or [TableName][ColumnName]
            if '[' in source_str and ']' in source_str:
                try:
                    # Get first bracketed part (table name)
                    first_bracket = source_str.find('[')
                    end_bracket = source_str.find(']', first_bracket)
                    if first_bracket >= 0 and end_bracket > first_bracket:
                        physical_table = source_str[first_bracket + 1:end_bracket]
                        if physical_table:
                            return physical_table
                except:
                    pass
        
        return None
    
    def _extract_physical_column_name(self, row, semantic_column_name):
        """Extract physical column name from a row"""
        # First try Source Column field
        source = row.get('Source Column', '')
        if pd.notna(source) and str(source).strip():
            source_str = str(source).strip()
            
            # Pattern 1: [TableName][ColumnName] - get last bracketed part
            if '[' in source_str and ']' in source_str:
                try:
                    # Find all bracketed parts
                    brackets = re.findall(r'\[([^\]]+)\]', source_str)
                    if brackets:
                        # Last bracketed part is usually the column name
                        physical_col = brackets[-1]
                        if physical_col:
                            return physical_col
                except:
                    pass
            
            # Pattern 2: Simple column name without brackets
            if source_str and '[' not in source_str:
                return source_str
        
        # Fallback: return the semantic column name as physical (direct mapping)
        return semantic_column_name
    
    def _classify_tables(self):
        """Classify tables as Fact or Dimension based on naming conventions"""
        tables = self.columns_df['Table'].dropna().unique()
        
        for table in tables:
            table_str = safe_str(table)
            if not table_str:
                continue
                
            table_lower = table_str.lower()
            # Fact table indicators
            if any(prefix in table_lower for prefix in ['fact', 'fact_', 'fact -']):
                self.fact_tables.append(table_str)
            # Dimension table indicators
            elif any(prefix in table_lower for prefix in ['dim', 'dim_', 'dimension']):
                self.dim_tables.append(table_str)
            else:
                # Check relationships to determine if it's a fact or dimension
                # Tables with many outgoing relationships are likely facts
                outgoing = len(self.relationships_df[self.relationships_df['From Table'] == table])
                incoming = len(self.relationships_df[self.relationships_df['To Table'] == table])
                
                if outgoing > incoming:
                    self.fact_tables.append(table_str)
                else:
                    self.dim_tables.append(table_str)
    
    def get_tables_summary(self):
        """Create tables overview summary with Semantic Model Name as first column"""
        summary = []
        
        for table in self.columns_df['Table'].dropna().unique():
            table_str = safe_str(table)
            if not table_str:
                continue
                
            table_data = self.columns_df[self.columns_df['Table'] == table]
            
            # Determine table type
            if table_str in self.fact_tables:
                table_type = "Fact"
            elif table_str in self.dim_tables:
                table_type = "Dimension"
            else:
                table_type = "Other"
            
            # Get physical table name from cache
            physical_table = self._physical_table_cache.get(table_str, '')
            
            # Count relationships
            outgoing_rels = len(self.relationships_df[self.relationships_df['From Table'] == table])
            incoming_rels = len(self.relationships_df[self.relationships_df['To Table'] == table])
            
            # Get related tables
            related_tables = self._get_related_tables(table_str)
            
            # Get key columns - safely handle Is Key column
            key_cols = []
            if 'Is Key' in table_data.columns:
                for _, row in table_data.iterrows():
                    is_key = safe_lower(row.get('Is Key', ''))
                    if is_key == 'true':
                        key_cols.append(safe_str(row.get('Column', '')))
            
            # Get hidden column count - safely handle Is Hidden column
            hidden_cols = 0
            if 'Is Hidden' in table_data.columns:
                for _, row in table_data.iterrows():
                    is_hidden = safe_lower(row.get('Is Hidden', ''))
                    if is_hidden == 'true':
                        hidden_cols += 1
            
            # Get description safely
            description = ''
            if not table_data.empty and 'Table Description' in table_data.columns:
                desc_val = table_data['Table Description'].iloc[0]
                description = safe_str(desc_val)
            
            # Get storage mode safely
            storage_mode = ''
            if not table_data.empty and 'Storage Mode' in table_data.columns:
                storage_val = table_data['Storage Mode'].iloc[0]
                storage_mode = safe_str(storage_val)
            
            summary.append({
                'Semantic Model': self.semantic_model_name,
                'Semantic Table': table_str,
                'Table Type': table_type,
                'Physical/ETL Source Table': safe_str(physical_table),
                'Description': description,
                'Column Count': len(table_data),
                'Key Columns': ', '.join(key_cols) if key_cols else '',
                'Hidden Columns': hidden_cols,
                'Storage Mode': storage_mode,
                'Outgoing Relationships': outgoing_rels,
                'Incoming Relationships': incoming_rels,
                'Related Tables': ', '.join(related_tables) if related_tables else ''
            })
        
        return pd.DataFrame(summary)
    
    def get_columns_glossary(self):
        """Create detailed columns glossary with Semantic Model Name as first column and physical info"""
        glossary_data = []
        
        for _, row in self.columns_df.iterrows():
            table_name = safe_str(row.get('Table', ''))
            column_name = safe_str(row.get('Column', ''))
            
            if not table_name or not column_name:
                continue
            
            # Determine table type
            if table_name in self.fact_tables:
                table_type = 'Fact'
            elif table_name in self.dim_tables:
                table_type = 'Dimension'
            else:
                table_type = 'Other'
            
            # Get physical table/column from cache
            physical_table = self._physical_table_cache.get(table_name, '')
            physical_column = self._physical_column_cache.get((table_name, column_name), '')
            
            # If physical column is same as semantic column, it's a direct mapping
            if not physical_column or physical_column == column_name:
                physical_column = column_name  # Direct mapping
            
            # If physical table is empty, use table name
            if not physical_table:
                physical_table = table_name
            
            # Check if this column is used in relationships
            is_relationship_key = self._is_column_in_relationship(table_name, column_name)
            
            glossary_data.append({
                'Semantic Model': self.semantic_model_name,
                'Table Type': table_type,
                'Semantic Table': table_name,
                'Semantic Column': column_name,
                'Physical/ETL Source Table': safe_str(physical_table),
                'Physical/ETL Source Column': safe_str(physical_column),
                'Column Description': safe_str(row.get('Column Description', '')),
                'Data Type': safe_str(row.get('Data Type', '')),
                'Column Type': safe_str(row.get('Column Type', '')),
                'Is Key': safe_str(row.get('Is Key', '')),
                'Is Hidden': safe_str(row.get('Is Hidden', '')),
                'Is Relationship Key': 'Yes' if is_relationship_key else 'No',
                'Format String': safe_str(row.get('Format String', '')),
                'Data Category': safe_str(row.get('Data Category', '')),
                'Summarize By': safe_str(row.get('Summarize By', ''))
            })
        
        return pd.DataFrame(glossary_data)
    
    def get_measures_glossary(self):
        """Create measures glossary with Semantic Model Name as first column and DAX explanations"""
        measures_data = []
        
        # Print column names for debugging (only once)
        if not hasattr(self, '_measures_columns_printed'):
            print(f"   📋 Measures CSV columns: {list(self.measures_df.columns)}")
            print(f"   📋 Detected measure name column: '{self.measure_name_column}'")
            self._measures_columns_printed = True
        
        for _, row in self.measures_df.iterrows():
            table_name = safe_str(row.get('Table', ''))
            
            # Get measure type (Measure, Calculated Table, etc.)
            measure_type = safe_str(row.get('Type', ''))
            
            # Get measure name using detected column
            measure_name = safe_str(row.get(self.measure_name_column, ''))
            
            # If measure name is still empty or same as type, try other common column names
            if not measure_name or measure_name in ['Measure', 'Calculated Table', 'Column']:
                for col in ['Measure', 'Name', 'Measure Name', 'MeasureName', 'Object Name', 'Object']:
                    if col in row.index and col != 'Type':
                        candidate = safe_str(row.get(col, ''))
                        if candidate and candidate not in ['Measure', 'Calculated Table', 'Column']:
                            measure_name = candidate
                            break
            
            # Get referenced tables and columns from DAX
            dax_expr = safe_str(row.get('DAX Expression', ''))
            if not dax_expr:
                dax_expr = safe_str(row.get('Expression', ''))  # Alternative column name
            
            referenced_tables, referenced_columns = self._parse_dax_references(dax_expr)
            
            measures_data.append({
                'Semantic Model': self.semantic_model_name,
                'Semantic Table': table_name,
                'Measure Name': measure_name,
                'Type': measure_type,
                'Description': safe_str(row.get('Description', '')),
                'DAX Expression': dax_expr,
                'DAX Explanation': self._explain_dax(dax_expr),
                'Is Hidden': safe_str(row.get('Is Hidden', '')),
                'Format String': safe_str(row.get('Format String', '')),
                'Display Folder': safe_str(row.get('Display Folder', '')),
                'Referenced Tables': ', '.join(referenced_tables) if referenced_tables else '',
                'Referenced Columns': ', '.join(referenced_columns) if referenced_columns else ''
            })
        
        return pd.DataFrame(measures_data)
    
    def get_relationships_glossary(self):
        """Create enhanced relationships glossary with physical table/column info"""
        relationships_data = []
        
        for _, rel in self.relationships_df.iterrows():
            from_table = safe_str(rel.get('From Table', ''))
            from_column = safe_str(rel.get('From Column', ''))
            to_table = safe_str(rel.get('To Table', ''))
            to_column = safe_str(rel.get('To Column', ''))
            
            if not from_table or not to_table:
                continue
            
            # Get physical table/column names from cache
            from_physical_table = self._physical_table_cache.get(from_table, '')
            from_physical_column = self._physical_column_cache.get((from_table, from_column), '')
            to_physical_table = self._physical_table_cache.get(to_table, '')
            to_physical_column = self._physical_column_cache.get((to_table, to_column), '')
            
            # If physical values are empty, use semantic values (direct mapping)
            if not from_physical_table:
                from_physical_table = from_table
            if not from_physical_column:
                from_physical_column = from_column
            if not to_physical_table:
                to_physical_table = to_table
            if not to_physical_column:
                to_physical_column = to_column
            
            # Determine table types
            from_table_type = 'Fact' if from_table in self.fact_tables else ('Dimension' if from_table in self.dim_tables else 'Other')
            to_table_type = 'Fact' if to_table in self.fact_tables else ('Dimension' if to_table in self.dim_tables else 'Other')
            
            # Interpret cardinality
            from_card = safe_str(rel.get('From Cardinality', ''))
            to_card = safe_str(rel.get('To Cardinality', ''))
            cardinality_desc = self._interpret_cardinality(from_card, to_card)
            
            # Get cross-filter direction and description
            cross_filter = safe_str(rel.get('Cross Filter Direction', ''))
            cross_filter_desc = self._interpret_cross_filter(cross_filter)
            
            relationships_data.append({
                'Semantic Model': self.semantic_model_name,
                'Relationship ID': safe_str(rel.get('Relationship ID', '')),
                'From Semantic Table': from_table,
                'From Table Type': from_table_type,
                'From Semantic Column': from_column,
                'From Physical/ETL Source Table': safe_str(from_physical_table),
                'From Physical/ETL Source Column': safe_str(from_physical_column),
                'To Semantic Table': to_table,
                'To Table Type': to_table_type,
                'To Semantic Column': to_column,
                'To Physical/ETL Source Table': safe_str(to_physical_table),
                'To Physical/ETL Source Column': safe_str(to_physical_column),
                'From Cardinality': from_card,
                'To Cardinality': to_card,
                'Cardinality Description': cardinality_desc,
                'Cross Filter Direction': cross_filter,
                'Cross Filter Behavior': cross_filter_desc,
                'Is Active': safe_str(rel.get('Is Active', '')),
                'Security Filtering': safe_str(rel.get('Security Filtering', ''))
            })
        
        return pd.DataFrame(relationships_data)
    
    def get_data_lineage_summary(self):
        """Create a data lineage summary showing physical to semantic mapping"""
        lineage_data = []
        
        for _, row in self.columns_df.iterrows():
            table_name = safe_str(row.get('Table', ''))
            column_name = safe_str(row.get('Column', ''))
            
            if not table_name or not column_name:
                continue
            
            # Get physical info
            physical_table = self._physical_table_cache.get(table_name, '')
            physical_column = self._physical_column_cache.get((table_name, column_name), '')
            
            # Use semantic names as fallback for physical
            if not physical_table:
                physical_table = table_name
            if not physical_column:
                physical_column = column_name
            
            table_type = 'Fact' if table_name in self.fact_tables else ('Dimension' if table_name in self.dim_tables else 'Other')
            
            # Determine transformation type
            transformation = 'Direct Mapping'
            if physical_column and physical_column.lower() != column_name.lower():
                transformation = 'Column Renamed'
            if physical_table and physical_table.lower() != table_name.lower():
                transformation = 'Table Renamed' if transformation == 'Direct Mapping' else 'Table & Column Renamed'
            
            lineage_data.append({
                'Semantic Model': self.semantic_model_name,
                'Physical/ETL Source Table': safe_str(physical_table),
                'Physical/ETL Source Column': safe_str(physical_column),
                'Semantic Table': table_name,
                'Semantic Column': column_name,
                'Table Type': table_type,
                'Data Type': safe_str(row.get('Data Type', '')),
                'Transformation': transformation
            })
        
        return pd.DataFrame(lineage_data)
    
    def get_key_columns_summary(self):
        """Create a summary of all key columns used in relationships"""
        key_data = []
        
        # Get unique relationship columns
        relationship_cols = set()
        for _, rel in self.relationships_df.iterrows():
            from_table = safe_str(rel.get('From Table', ''))
            from_col = safe_str(rel.get('From Column', ''))
            to_table = safe_str(rel.get('To Table', ''))
            to_col = safe_str(rel.get('To Column', ''))
            
            if from_table and from_col:
                relationship_cols.add((from_table, from_col))
            if to_table and to_col:
                relationship_cols.add((to_table, to_col))
        
        for table_name, column_name in relationship_cols:
            # Get column details
            col_data = self.columns_df[
                (self.columns_df['Table'] == table_name) & 
                (self.columns_df['Column'] == column_name)
            ]
            
            physical_table = self._physical_table_cache.get(table_name, '')
            physical_column = self._physical_column_cache.get((table_name, column_name), '')
            
            # Use semantic names as fallback for physical
            if not physical_table:
                physical_table = table_name
            if not physical_column:
                physical_column = column_name
            
            table_type = 'Fact' if table_name in self.fact_tables else ('Dimension' if table_name in self.dim_tables else 'Other')
            
            # Find related tables through this key
            related = []
            for _, rel in self.relationships_df.iterrows():
                rel_from_table = safe_str(rel.get('From Table', ''))
                rel_from_col = safe_str(rel.get('From Column', ''))
                rel_to_table = safe_str(rel.get('To Table', ''))
                rel_to_col = safe_str(rel.get('To Column', ''))
                
                if rel_from_table == table_name and rel_from_col == column_name:
                    related.append(rel_to_table)
                elif rel_to_table == table_name and rel_to_col == column_name:
                    related.append(rel_from_table)
            
            # Get data type and is_key from columns_df if available
            data_type = ''
            is_primary_key = ''
            if not col_data.empty:
                row = col_data.iloc[0]
                data_type = safe_str(row.get('Data Type', ''))
                is_primary_key = safe_str(row.get('Is Key', ''))
            
            key_data.append({
                'Semantic Model': self.semantic_model_name,
                'Semantic Table': table_name,
                'Table Type': table_type,
                'Key Column': column_name,
                'Physical/ETL Source Table': safe_str(physical_table),
                'Physical/ETL Source Column': safe_str(physical_column),
                'Data Type': data_type,
                'Is Primary Key': is_primary_key,
                'Related Tables': ', '.join(related) if related else ''
            })
        
        return pd.DataFrame(key_data)
    
    def get_hidden_objects_summary(self):
        """Create a summary of all hidden columns and measures"""
        hidden_data = []
        
        # Hidden columns
        for _, row in self.columns_df.iterrows():
            is_hidden = safe_lower(row.get('Is Hidden', ''))
            if is_hidden == 'true':
                table_name = safe_str(row.get('Table', ''))
                column_name = safe_str(row.get('Column', ''))
                
                if not table_name or not column_name:
                    continue
                
                physical_table = self._physical_table_cache.get(table_name, '')
                physical_column = self._physical_column_cache.get((table_name, column_name), '')
                
                # Use semantic names as fallback for physical
                if not physical_table:
                    physical_table = table_name
                if not physical_column:
                    physical_column = column_name
                
                hidden_data.append({
                    'Semantic Model': self.semantic_model_name,
                    'Object Type': 'Column',
                    'Semantic Table': table_name,
                    'Object Name': column_name,
                    'Physical/ETL Source Table': safe_str(physical_table),
                    'Physical/ETL Source Column': safe_str(physical_column),
                    'Description': safe_str(row.get('Column Description', '')),
                    'Reason for Hiding': 'Technical column / Not for end-user reporting'
                })
        
        # Hidden measures
        if 'Is Hidden' in self.measures_df.columns:
            for _, row in self.measures_df.iterrows():
                is_hidden = safe_lower(row.get('Is Hidden', ''))
                if is_hidden == 'true':
                    # Get measure name using detected column
                    measure_name = safe_str(row.get(self.measure_name_column, ''))
                    
                    # If measure name is empty or same as type, try other common column names
                    if not measure_name or measure_name in ['Measure', 'Calculated Table', 'Column']:
                        for col in ['Measure', 'Name', 'Measure Name', 'MeasureName', 'Object Name', 'Object']:
                            if col in row.index and col != 'Type':
                                candidate = safe_str(row.get(col, ''))
                                if candidate and candidate not in ['Measure', 'Calculated Table', 'Column']:
                                    measure_name = candidate
                                    break
                    
                    # Get measure type
                    measure_type = safe_str(row.get('Type', 'Measure'))
                    
                    hidden_data.append({
                        'Semantic Model': self.semantic_model_name,
                        'Object Type': measure_type if measure_type else 'Measure',
                        'Semantic Table': safe_str(row.get('Table', '')),
                        'Object Name': measure_name,
                        'Physical/ETL Source Table': '',
                        'Physical/ETL Source Column': '',
                        'Description': safe_str(row.get('Description', '')),
                        'Reason for Hiding': 'Intermediate calculation / Not for end-user reporting'
                    })
        
        return pd.DataFrame(hidden_data)
    
    def get_model_statistics(self):
        """Create model-level statistics summary"""
        stats = []
        
        # Basic counts
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Tables',
            'Metric': 'Total Tables',
            'Value': len(self.columns_df['Table'].dropna().unique()),
            'Details': ''
        })
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Tables',
            'Metric': 'Fact Tables',
            'Value': len(self.fact_tables),
            'Details': ', '.join(self.fact_tables) if self.fact_tables else ''
        })
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Tables',
            'Metric': 'Dimension Tables',
            'Value': len(self.dim_tables),
            'Details': ', '.join(self.dim_tables) if self.dim_tables else ''
        })
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Columns',
            'Metric': 'Total Columns',
            'Value': len(self.columns_df),
            'Details': ''
        })
        
        # Count hidden columns safely
        hidden_count = 0
        for _, row in self.columns_df.iterrows():
            if safe_lower(row.get('Is Hidden', '')) == 'true':
                hidden_count += 1
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Columns',
            'Metric': 'Hidden Columns',
            'Value': hidden_count,
            'Details': ''
        })
        
        # Count key columns safely
        key_count = 0
        for _, row in self.columns_df.iterrows():
            if safe_lower(row.get('Is Key', '')) == 'true':
                key_count += 1
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Columns',
            'Metric': 'Key Columns',
            'Value': key_count,
            'Details': ''
        })
        
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Measures',
            'Metric': 'Total Measures',
            'Value': len(self.measures_df),
            'Details': ''
        })
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Relationships',
            'Metric': 'Total Relationships',
            'Value': len(self.relationships_df),
            'Details': ''
        })
        
        # Data types distribution
        if 'Data Type' in self.columns_df.columns:
            data_type_counts = self.columns_df['Data Type'].dropna().value_counts()
            for dtype, count in data_type_counts.items():
                if pd.notna(dtype):
                    stats.append({
                        'Semantic Model': self.semantic_model_name,
                        'Category': 'Data Types',
                        'Metric': f'{dtype} Columns',
                        'Value': count,
                        'Details': ''
                    })
        
        # Storage modes if available
        if 'Storage Mode' in self.columns_df.columns:
            storage_counts = self.columns_df.groupby('Table')['Storage Mode'].first().dropna().value_counts()
            for mode, count in storage_counts.items():
                if pd.notna(mode):
                    stats.append({
                        'Semantic Model': self.semantic_model_name,
                        'Category': 'Storage',
                        'Metric': f'{mode} Tables',
                        'Value': count,
                        'Details': ''
                    })
        
        return pd.DataFrame(stats)
    
    def _get_related_tables(self, table_name):
        """Get list of tables related to a given table"""
        related = set()
        
        for _, rel in self.relationships_df.iterrows():
            from_table = safe_str(rel.get('From Table', ''))
            to_table = safe_str(rel.get('To Table', ''))
            
            if from_table == table_name:
                related.add(to_table)
            elif to_table == table_name:
                related.add(from_table)
        
        return list(related)
    
    def _is_column_in_relationship(self, table_name, column_name):
        """Check if a column is used in any relationship"""
        for _, rel in self.relationships_df.iterrows():
            from_table = safe_str(rel.get('From Table', ''))
            from_col = safe_str(rel.get('From Column', ''))
            to_table = safe_str(rel.get('To Table', ''))
            to_col = safe_str(rel.get('To Column', ''))
            
            if (from_table == table_name and from_col == column_name) or \
               (to_table == table_name and to_col == column_name):
                return True
        return False
    
    def _parse_dax_references(self, dax_formula):
        """Parse DAX formula to extract referenced tables and columns"""
        if not dax_formula:
            return [], []
        
        tables = set()
        columns = set()
        dax = str(dax_formula)
        
        # Pattern: 'Table Name'[Column Name] or Table[Column]
        # Match table[column] patterns
        pattern = r"'?([^'\[\]]+)'?\[([^\]]+)\]"
        matches = re.findall(pattern, dax)
        
        for table, column in matches:
            tables.add(table.strip())
            columns.add(f"{table.strip()}[{column}]")
        
        return list(tables), list(columns)
    
    def _interpret_cardinality(self, from_card, to_card):
        """Interpret cardinality values to human-readable description"""
        if from_card == '2' and to_card == '1':
            return "Many-to-One (*:1)"
        elif from_card == '1' and to_card == '2':
            return "One-to-Many (1:*)"
        elif from_card == '1' and to_card == '1':
            return "One-to-One (1:1)"
        elif from_card == '2' and to_card == '2':
            return "Many-to-Many (*:*)"
        else:
            return f"From:{from_card} To:{to_card}"
    
    def _interpret_cross_filter(self, cross_filter):
        """Interpret cross-filter direction to human-readable description"""
        if not cross_filter:
            return ""
        
        cf = cross_filter.lower()
        if cf in ['1', 'single', 'onedirection']:
            return "Single direction - filters flow from 'One' side to 'Many' side"
        elif cf in ['2', 'both', 'bidirectional']:
            return "Bidirectional - filters flow in both directions"
        elif cf in ['3', 'automatic']:
            return "Automatic - Power BI determines filter direction"
        else:
            return cross_filter
    
    def _explain_dax(self, dax_formula):
        """Provide simple explanation for DAX formulas"""
        if not dax_formula:
            return ""
        
        dax = str(dax_formula).upper()
        
        explanations = []
        
        if 'SUM(' in dax:
            explanations.append("SUM aggregation")
        if 'CALCULATE(' in dax:
            explanations.append("Context modification")
        if 'SUMX(' in dax:
            explanations.append("Row iteration with sum")
        if 'DIVIDE(' in dax:
            explanations.append("Safe division")
        if 'COUNTROWS(' in dax:
            explanations.append("Row count")
        if 'AVERAGE(' in dax or 'AVERAGEX(' in dax:
            explanations.append("Average calculation")
        if 'FILTER(' in dax:
            explanations.append("Filtered context")
        if 'ALL(' in dax or 'ALLEXCEPT(' in dax:
            explanations.append("Removes filters")
        if 'RELATED(' in dax:
            explanations.append("Uses relationship")
        if 'RELATEDTABLE(' in dax:
            explanations.append("Uses related table")
        if 'IF(' in dax or 'SWITCH(' in dax:
            explanations.append("Conditional logic")
        if 'DISTINCTCOUNT(' in dax:
            explanations.append("Distinct count")
        if 'MAX(' in dax or 'MIN(' in dax:
            explanations.append("Min/Max aggregation")
        if 'DATESYTD(' in dax or 'DATESMTD(' in dax or 'DATESQTD(' in dax:
            explanations.append("Time intelligence")
        if 'PREVIOUSYEAR(' in dax or 'SAMEPERIODLASTYEAR(' in dax:
            explanations.append("Year-over-year comparison")
        
        return '; '.join(explanations) if explanations else "Custom calculation"
    
    def generate_dbml(self, output_file='semantic_model.dbml'):
        """Generate DBML file with star schema layout"""
        dbml_content = []
        
        # Header
        dbml_content.append("// Power BI Semantic Model - Star Schema")
        dbml_content.append(f"// Semantic Model: {self.semantic_model_name}")
        dbml_content.append(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        dbml_content.append("// Star Schema: Facts in center, Dimensions around them\n")
        
        # Project definition
        safe_name = self._sanitize_name(self.semantic_model_name)
        dbml_content.append(f"Project {safe_name} {{")
        dbml_content.append("  database_type: 'Power BI'")
        dbml_content.append(f"  Note: 'Semantic Model: {self.semantic_model_name}'")
        dbml_content.append("}\n")
        
        # Generate Fact Tables first (center of star schema)
        dbml_content.append("// ===== FACT TABLES =====")
        for table in self.fact_tables:
            dbml_content.append(self._generate_table_dbml(table, is_fact=True))
        
        dbml_content.append("\n// ===== DIMENSION TABLES =====")
        for table in self.dim_tables:
            dbml_content.append(self._generate_table_dbml(table, is_fact=False))
        
        # Generate relationships
        dbml_content.append("\n// ===== RELATIONSHIPS =====")
        dbml_content.extend(self._generate_relationships_dbml())
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(dbml_content))
        
        print(f"   ✅ DBML file generated: {output_file}")
        return output_file
    
    def _generate_table_dbml(self, table_name, is_fact=False):
        """Generate DBML for a single table"""
        table_data = self.columns_df[self.columns_df['Table'] == table_name]
        
        if table_data.empty:
            return ""
        
        # Get physical table name from cache
        physical_table = self._physical_table_cache.get(table_name)
        
        # Sanitize table name
        safe_table_name = self._sanitize_name(table_name)
        
        dbml = [f"\nTable {safe_table_name} {{"]
        
        # Add physical table name in comment
        if physical_table and safe_lower(physical_table) != safe_lower(table_name):
            dbml.append(f"  // Physical/Source Table: {physical_table}")
        
        # Add table description if available
        if 'Table Description' in table_data.columns:
            table_desc = table_data['Table Description'].iloc[0]
            if pd.notna(table_desc):
                escaped_desc = safe_str(table_desc).replace("'", "\\'").replace('\n', ' ').replace('\r', '')
                dbml.append(f"  Note: '{escaped_desc}'")
        
        # Map data types
        type_map = {
            'Int64': 'bigint',
            'String': 'varchar',
            'Decimal': 'decimal',
            'Double': 'double',
            'DateTime': 'datetime',
            'Boolean': 'boolean',
            'Date': 'date'
        }
        
        # Add columns
        for _, col in table_data.iterrows():
            col_name = safe_str(col.get('Column', ''))
            if not col_name:
                continue
            
            safe_col_name = self._sanitize_name(col_name)
            
            pbi_type = safe_str(col.get('Data Type', 'varchar'))
            data_type = type_map.get(pbi_type, 'varchar')
            
            # Build column definition
            col_def = f"  {safe_col_name} {data_type}"
            
            # Add primary key indicator
            if safe_lower(col.get('Is Key', '')) == 'true':
                col_def += " [pk]"
            
            # Build note with description and physical column name
            note_parts = []
            
            # Add column description
            col_desc = col.get('Column Description')
            if pd.notna(col_desc) and col_desc:
                escaped = safe_str(col_desc).replace("'", "\\'").replace('\n', ' ').replace('\r', '')
                note_parts.append(escaped)
            
            # Add physical source info from cache
            physical_col = self._physical_column_cache.get((table_name, col_name))
            if physical_col and safe_lower(physical_col) != safe_lower(col_name):
                note_parts.append(f"Physical Column: {physical_col}")
            
            # Add source table if different
            if physical_table and safe_lower(physical_table) != safe_lower(table_name):
                note_parts.append(f"Source Table: {physical_table}")
            
            if note_parts:
                col_def += f" [note: '{' | '.join(note_parts)}']"
            
            dbml.append(col_def)
        
        dbml.append("}")
        
        return '\n'.join(dbml)
    
    def _generate_relationships_dbml(self):
        """Generate DBML relationships"""
        relationships = []
        
        for _, rel in self.relationships_df.iterrows():
            from_table = safe_str(rel.get('From Table', ''))
            from_col = safe_str(rel.get('From Column', ''))
            to_table = safe_str(rel.get('To Table', ''))
            to_col = safe_str(rel.get('To Column', ''))
            
            if not from_table or not to_table or not from_col or not to_col:
                continue
            
            safe_from_table = self._sanitize_name(from_table)
            safe_from_col = self._sanitize_name(from_col)
            safe_to_table = self._sanitize_name(to_table)
            safe_to_col = self._sanitize_name(to_col)
            
            # Determine relationship type
            from_card = safe_str(rel.get('From Cardinality', ''))
            to_card = safe_str(rel.get('To Cardinality', ''))
            
            if from_card == '2' and to_card == '1':
                rel_type = ">"  # many-to-one
            elif from_card == '1' and to_card == '2':
                rel_type = "<"  # one-to-many
            elif from_card == '1' and to_card == '1':
                rel_type = "-"  # one-to-one
            else:
                rel_type = ">"  # default to many-to-one
            
            # Add relationship
            rel_line = f"Ref: {safe_from_table}.{safe_from_col} {rel_type} {safe_to_table}.{safe_to_col}"
            
            # Add cross-filter direction as note
            cross_filter = rel.get('Cross Filter Direction')
            if pd.notna(cross_filter):
                rel_line += f" [note: 'Cross-filter: {cross_filter}']"
            
            relationships.append(rel_line)
        
        return relationships
    
    def _sanitize_name(self, name):
        """Sanitize table/column names for DBML"""
        if pd.isna(name) or name is None:
            return "unknown"
        name = str(name).strip()
        # Replace spaces and special characters
        name = name.replace(' ', '_').replace('-', '_').replace('/', '_')
        # Remove invalid characters
        name = ''.join(c for c in name if c.isalnum() or c == '_')
        return name if name else "unknown"


class MultiModelDocumentationGenerator:
    """Generator that handles multiple semantic models and combines them into one output"""
    
    def __init__(self, source_directory, mapping_file=None):
        """Initialize with source directory containing semantic model CSV files
        
        Args:
            source_directory: Path to directory containing *_COLUMNS.csv, *_MEASURES.csv, *_RELATIONSHIPS.csv files
            mapping_file: Optional path to mapping file (CSV or Excel)
        """
        self.source_directory = source_directory
        self.mapping_df = None
        
        # Read mapping file if provided
        if mapping_file and os.path.exists(mapping_file):
            if mapping_file.endswith('.xlsx') or mapping_file.endswith('.xls'):
                self.mapping_df = pd.read_excel(mapping_file)
            else:
                try:
                    self.mapping_df = pd.read_csv(mapping_file, encoding='utf-8')
                except UnicodeDecodeError:
                    self.mapping_df = pd.read_csv(mapping_file, encoding='latin-1')
        
        # Discover semantic models
        self.semantic_models = self._discover_semantic_models()
        
    def _discover_semantic_models(self):
        """Discover all semantic models in the source directory based on file naming pattern"""
        models = {}
        
        # Find all COLUMNS files
        columns_files = glob.glob(os.path.join(self.source_directory, '*_COLUMNS.csv'))
        
        for columns_file in columns_files:
            # Extract semantic model name from file name
            base_name = os.path.basename(columns_file)
            # Remove _COLUMNS.csv suffix to get model name
            model_name = base_name.replace('_COLUMNS.csv', '')
            
            # Check if corresponding MEASURES and RELATIONSHIPS files exist
            measures_file = os.path.join(self.source_directory, f'{model_name}_MEASURES.csv')
            relationships_file = os.path.join(self.source_directory, f'{model_name}_RELATIONSHIPS.csv')
            
            if os.path.exists(measures_file) and os.path.exists(relationships_file):
                models[model_name] = {
                    'columns_file': columns_file,
                    'measures_file': measures_file,
                    'relationships_file': relationships_file
                }
            else:
                # Check for partial matches (missing files)
                missing = []
                if not os.path.exists(measures_file):
                    missing.append('MEASURES')
                if not os.path.exists(relationships_file):
                    missing.append('RELATIONSHIPS')
                print(f"⚠️  Semantic Model '{model_name}' is missing files: {', '.join(missing)}")
        
        return models
    
    def _read_csv_with_encoding(self, file_path):
        """Read CSV file with encoding fallback"""
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='latin-1')
    
    def generate_combined_glossary(self, output_file='semantic_model_glossary.xlsx'):
        """Generate a combined glossary Excel file with all semantic models"""
        
        if not self.semantic_models:
            print("❌ No complete semantic models found in the directory.")
            return None
        
        print(f"\n🚀 Processing {len(self.semantic_models)} Semantic Model(s)...\n")
        
        # Initialize combined DataFrames
        all_tables_summary = []
        all_columns_glossary = []
        all_measures_glossary = []
        all_relationships = []
        all_data_lineage = []
        all_key_columns = []
        all_hidden_objects = []
        all_model_stats = []
        
        # Process each semantic model
        for model_name, files in sorted(self.semantic_models.items()):
            print(f"📊 Processing: {model_name}")
            
            try:
                # Read CSV files
                columns_df = self._read_csv_with_encoding(files['columns_file'])
                measures_df = self._read_csv_with_encoding(files['measures_file'])
                relationships_df = self._read_csv_with_encoding(files['relationships_file'])
                
                # Create generator for this model
                generator = PowerBIDocumentationGenerator(
                    columns_df=columns_df,
                    measures_df=measures_df,
                    relationships_df=relationships_df,
                    semantic_model_name=model_name,
                    mapping_df=self.mapping_df
                )
                
                # Get data for each sheet
                all_tables_summary.append(generator.get_tables_summary())
                all_columns_glossary.append(generator.get_columns_glossary())
                all_measures_glossary.append(generator.get_measures_glossary())
                all_relationships.append(generator.get_relationships_glossary())
                all_data_lineage.append(generator.get_data_lineage_summary())
                all_key_columns.append(generator.get_key_columns_summary())
                all_hidden_objects.append(generator.get_hidden_objects_summary())
                all_model_stats.append(generator.get_model_statistics())
                
                print(f"   ✅ Processed: {len(columns_df)} columns, {len(measures_df)} measures, {len(relationships_df)} relationships")
                
            except Exception as e:
                print(f"   ❌ Error processing {model_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Combine all DataFrames
        print(f"\n📝 Combining data from all models...")
        
        combined_tables = pd.concat(all_tables_summary, ignore_index=True) if all_tables_summary else pd.DataFrame()
        combined_columns = pd.concat(all_columns_glossary, ignore_index=True) if all_columns_glossary else pd.DataFrame()
        combined_measures = pd.concat(all_measures_glossary, ignore_index=True) if all_measures_glossary else pd.DataFrame()
        combined_relationships = pd.concat(all_relationships, ignore_index=True) if all_relationships else pd.DataFrame()
        combined_lineage = pd.concat(all_data_lineage, ignore_index=True) if all_data_lineage else pd.DataFrame()
        combined_keys = pd.concat(all_key_columns, ignore_index=True) if all_key_columns else pd.DataFrame()
        combined_hidden = pd.concat(all_hidden_objects, ignore_index=True) if all_hidden_objects else pd.DataFrame()
        combined_stats = pd.concat(all_model_stats, ignore_index=True) if all_model_stats else pd.DataFrame()
        
        # Write to Excel
        print(f"📄 Writing to Excel: {output_file}")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Sheet 1: Tables Overview
            if not combined_tables.empty:
                combined_tables.to_excel(writer, sheet_name='Tables Overview', index=False)
            
            # Sheet 2: All Columns
            if not combined_columns.empty:
                combined_columns.to_excel(writer, sheet_name='Columns Glossary', index=False)
            
            # Sheet 3: All Measures
            if not combined_measures.empty:
                combined_measures.to_excel(writer, sheet_name='Measures Glossary', index=False)
            
            # Sheet 4: Relationships
            if not combined_relationships.empty:
                combined_relationships.to_excel(writer, sheet_name='Relationships', index=False)
            
            # Sheet 5: Data Lineage Summary
            if not combined_lineage.empty:
                combined_lineage.to_excel(writer, sheet_name='Data Lineage', index=False)
            
            # Sheet 6: Key Columns Summary
            if not combined_keys.empty:
                combined_keys.to_excel(writer, sheet_name='Key Columns', index=False)
            
            # Sheet 7: Hidden Objects
            if not combined_hidden.empty:
                combined_hidden.to_excel(writer, sheet_name='Hidden Objects', index=False)
            
            # Sheet 8: Model Summary Statistics
            if not combined_stats.empty:
                combined_stats.to_excel(writer, sheet_name='Model Statistics', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_cells = [cell for cell in column]
                    for cell in column_cells:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_cells[0].column_letter].width = adjusted_width
        
        print(f"\n✅ Glossary Excel generated: {output_file}")
        return output_file
    
    def generate_dbml_files(self, output_dir='output'):
        """Generate individual DBML files for each semantic model"""
        Path(output_dir).mkdir(exist_ok=True)
        
        generated_files = []
        
        for model_name, files in sorted(self.semantic_models.items()):
            try:
                columns_df = self._read_csv_with_encoding(files['columns_file'])
                measures_df = self._read_csv_with_encoding(files['measures_file'])
                relationships_df = self._read_csv_with_encoding(files['relationships_file'])
                
                generator = PowerBIDocumentationGenerator(
                    columns_df=columns_df,
                    measures_df=measures_df,
                    relationships_df=relationships_df,
                    semantic_model_name=model_name,
                    mapping_df=self.mapping_df
                )
                
                # Generate DBML
                safe_name = model_name.replace(' ', '_').replace('-', '_')
                safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
                dbml_file = os.path.join(output_dir, f'{safe_name}.dbml')
                generator.generate_dbml(dbml_file)
                generated_files.append(dbml_file)
                
            except Exception as e:
                print(f"   ❌ Error generating DBML for {model_name}: {str(e)}")
        
        return generated_files
    
    def generate_all_documents(self, output_dir='output'):
        """Generate all documentation for all semantic models"""
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        print("=" * 60)
        print("🚀 Power BI Semantic Model Documentation Generator")
        print("=" * 60)
        print(f"\n📁 Source directory: {self.source_directory}")
        print(f"📁 Output directory: {output_dir}")
        print(f"📊 Discovered {len(self.semantic_models)} complete Semantic Model(s):")
        for model_name in sorted(self.semantic_models.keys()):
            print(f"   • {model_name}")
        
        # Generate combined glossary
        glossary_file = os.path.join(output_dir, 'semantic_model_glossary.xlsx')
        self.generate_combined_glossary(glossary_file)
        
        # Generate individual DBML files
        print(f"\n📐 Generating DBML files...")
        dbml_files = self.generate_dbml_files(output_dir)
        
        # Generate mapping if available
        if self.mapping_df is not None:
            mapping_output = os.path.join(output_dir, 'oracle_to_powerbi_mapping.xlsx')
            mapping_with_header = self.mapping_df.copy()
            mapping_with_header.to_excel(mapping_output, index=False)
            print(f"✅ Mapping file copied: {mapping_output}")
        
        print("\n" + "=" * 60)
        print("✅ All documents generated successfully!")
        print("=" * 60)
        print(f"\n📋 Generated files in '{output_dir}':")
        print(f"   1. semantic_model_glossary.xlsx - Combined glossary with 8 sheets:")
        print(f"      • Tables Overview")
        print(f"      • Columns Glossary")
        print(f"      • Measures Glossary")
        print(f"      • Relationships (with ETL source info)")
        print(f"      • Data Lineage")
        print(f"      • Key Columns")
        print(f"      • Hidden Objects")
        print(f"      • Model Statistics")
        
        if dbml_files:
            print(f"\n   2. DBML files ({len(dbml_files)} files):")
            for f in dbml_files:
                print(f"      • {os.path.basename(f)}")
        
        return glossary_file


# Example usage
if __name__ == "__main__":
    # Get the current working directory (where you're running the script from)
    current_directory = os.getcwd()
    
    print(f"📁 Current working directory: {current_directory}")
    print(f"📂 Looking for Semantic Model files in: {current_directory}\n")
    
    # Optional: Path to mapping file
    mapping_file = os.path.join(current_directory, 'RPDtoPBI_Mapping_Draft.xlsx')
    if not os.path.exists(mapping_file):
        mapping_file = None
        print(f"ℹ️  No mapping file found (RPDtoPBI_Mapping_Draft.xlsx)")
    else:
        print(f"✅ Found mapping file: RPDtoPBI_Mapping_Draft.xlsx")
    
    # Initialize the multi-model generator
    try:
        generator = MultiModelDocumentationGenerator(
            source_directory=current_directory,
            mapping_file=mapping_file
        )
        
        if generator.semantic_models:
            # Generate all documents
            generator.generate_all_documents(output_dir='powerbi_documentation')
        else:
            print("\n❌ No complete semantic models found.")
            print("\n📋 Looking for files matching pattern: *_COLUMNS.csv, *_MEASURES.csv, *_RELATIONSHIPS.csv")
            print("\n📋 Available CSV files in current directory:")
            for file in sorted(os.listdir(current_directory)):
                if file.endswith('.csv'):
                    print(f"   - {file}")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
