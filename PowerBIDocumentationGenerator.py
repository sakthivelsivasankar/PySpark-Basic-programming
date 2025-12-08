import pandas as pd
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class PowerBIDocumentationGenerator:
    def __init__(self, columns_file, measures_file, relationships_file, mapping_file=None, semantic_model_name=None):
        """Initialize with CSV file paths
        
        Args:
            columns_file: Path to columns CSV file
            measures_file: Path to measures CSV file
            relationships_file: Path to relationships CSV file
            mapping_file: Optional path to mapping file (CSV or Excel)
            semantic_model_name: Optional name for the semantic model. If not provided,
                                 it will be derived from the columns file name.
        """
        # Derive semantic model name from file name if not provided
        if semantic_model_name:
            self.semantic_model_name = semantic_model_name
        else:
            # Extract from columns file name (e.g., 'SemanticModelName_COLUMNS.csv' -> 'SemanticModelName')
            base_name = os.path.basename(columns_file)
            self.semantic_model_name = base_name.replace('_COLUMNS.csv', '').replace('_columns.csv', '')
            # Clean up common suffixes
            for suffix in ['_COLUMNS', '_columns', '_Columns']:
                if self.semantic_model_name.endswith(suffix):
                    self.semantic_model_name = self.semantic_model_name[:-len(suffix)]
        
        # Read CSV files with encoding fallback
        try:
            self.columns_df = pd.read_csv(columns_file, encoding='utf-8')
        except UnicodeDecodeError:
            self.columns_df = pd.read_csv(columns_file, encoding='latin-1')
        
        try:
            self.measures_df = pd.read_csv(measures_file, encoding='utf-8')
        except UnicodeDecodeError:
            self.measures_df = pd.read_csv(measures_file, encoding='latin-1')
        
        try:
            self.relationships_df = pd.read_csv(relationships_file, encoding='utf-8')
        except UnicodeDecodeError:
            self.relationships_df = pd.read_csv(relationships_file, encoding='latin-1')
        
        # Read mapping file - handle both CSV and Excel formats
        if mapping_file:
            if mapping_file.endswith('.xlsx') or mapping_file.endswith('.xls'):
                self.mapping_df = pd.read_excel(mapping_file)
            else:
                try:
                    self.mapping_df = pd.read_csv(mapping_file, encoding='utf-8')
                except UnicodeDecodeError:
                    self.mapping_df = pd.read_csv(mapping_file, encoding='latin-1')
        else:
            self.mapping_df = None
        
        # Build physical table/column lookup cache for performance
        self._build_physical_mapping_cache()
        
        # Identify fact and dimension tables
        self.fact_tables = []
        self.dim_tables = []
        self._classify_tables()
    
    def _build_physical_mapping_cache(self):
        """Build a cache of physical table and column mappings for quick lookup"""
        self._physical_table_cache = {}
        self._physical_column_cache = {}
        
        for _, row in self.columns_df.iterrows():
            table_name = row['Table']
            column_name = row['Column']
            
            # Cache physical table name
            if table_name not in self._physical_table_cache:
                physical_table = self._extract_physical_table_name(row)
                self._physical_table_cache[table_name] = physical_table
            
            # Cache physical column name
            cache_key = (table_name, column_name)
            physical_col = self._extract_physical_column_name(row)
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
        
        # Fallback: Source Column field
        source = row.get('Source Column', '')
        if pd.notna(source) and '[' in str(source) and ']' in str(source):
            try:
                physical_table = str(source).split('[')[1].split(']')[0]
                if physical_table:
                    return physical_table
            except:
                pass
        
        return None
    
    def _extract_physical_column_name(self, row):
        """Extract physical column name from a row"""
        # First try Source Column field
        source = row.get('Source Column', '')
        if pd.notna(source) and '[' in str(source):
            try:
                parts = str(source).split('[')
                if len(parts) >= 2:
                    col_part = parts[-1].split(']')[0]
                    if col_part:
                        return col_part
            except:
                pass
        
        # Fallback: Source Query/Expression
        source_query = row.get('Source Query/Expression', '')
        if pd.notna(source_query) and '[' in str(source_query):
            try:
                parts = str(source_query).split('[')
                if len(parts) >= 2:
                    col_part = parts[-1].split(']')[0]
                    if col_part and '.' not in col_part:
                        return col_part
            except:
                pass
        
        return None
    
    def _classify_tables(self):
        """Classify tables as Fact or Dimension based on naming conventions"""
        tables = self.columns_df['Table'].unique()
        
        for table in tables:
            table_lower = table.lower()
            # Fact table indicators
            if any(prefix in table_lower for prefix in ['fact', 'fact_', 'fact -']):
                self.fact_tables.append(table)
            # Dimension table indicators
            elif any(prefix in table_lower for prefix in ['dim', 'dim_', 'dimension']):
                self.dim_tables.append(table)
            else:
                # Check relationships to determine if it's a fact or dimension
                # Tables with many outgoing relationships are likely facts
                outgoing = len(self.relationships_df[self.relationships_df['From Table'] == table])
                incoming = len(self.relationships_df[self.relationships_df['To Table'] == table])
                
                if outgoing > incoming:
                    self.fact_tables.append(table)
                else:
                    self.dim_tables.append(table)
    
    def generate_dbml(self, output_file='semantic_model.dbml'):
        """Generate DBML file with star schema layout"""
        dbml_content = []
        
        # Header
        dbml_content.append("// Power BI Semantic Model - Star Schema")
        dbml_content.append(f"// Semantic Model: {self.semantic_model_name}")
        dbml_content.append(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        dbml_content.append("// Star Schema: Facts in center, Dimensions around them\n")
        
        # Project definition
        dbml_content.append(f"Project {self._sanitize_name(self.semantic_model_name)} {{")
        dbml_content.append("  database_type: 'Power BI'")
        dbml_content.append("  Note: 'Migrated from Oracle ADW/OBIEE to Microsoft Fabric'")
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
        
        print(f"✅ DBML file generated: {output_file}")
        return output_file
    
    def _generate_table_dbml(self, table_name, is_fact=False):
        """Generate DBML for a single table"""
        table_data = self.columns_df[self.columns_df['Table'] == table_name]
        
        if table_data.empty:
            return ""
        
        # Get physical table name from cache
        physical_table = self._physical_table_cache.get(table_name)
        
        dbml = [f"\nTable {self._sanitize_name(table_name)} {{"]
        
        # Add physical table name in comment
        if physical_table and physical_table.lower() != table_name.lower():
            dbml.append(f"  // Physical/Source Table: {physical_table}")
        
        # Add table description if available
        table_desc = table_data['Table Description'].iloc[0]
        if pd.notna(table_desc):
            dbml.append(f"  Note: '{self._escape_string(table_desc)}'")
        
        # Add columns
        for _, col in table_data.iterrows():
            col_name = self._sanitize_name(col['Column'])
            data_type = self._map_data_type(col['Data Type'])
            
            # Build column definition
            col_def = f"  {col_name} {data_type}"
            
            # Add primary key indicator
            if pd.notna(col['Is Key']) and str(col['Is Key']).lower() == 'true':
                col_def += " [pk]"
            
            # Build note with description and physical column name
            note_parts = []
            
            # Add column description
            if pd.notna(col['Column Description']):
                note_parts.append(self._escape_string(col['Column Description']))
            
            # Add physical source info from cache
            physical_col = self._physical_column_cache.get((table_name, col['Column']))
            if physical_col and physical_col.lower() != col['Column'].lower():
                note_parts.append(f"Physical Column: {physical_col}")
            
            # Add source table if different
            if physical_table and physical_table.lower() != table_name.lower():
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
            from_table = self._sanitize_name(rel['From Table'])
            from_col = self._sanitize_name(rel['From Column'])
            to_table = self._sanitize_name(rel['To Table'])
            to_col = self._sanitize_name(rel['To Column'])
            
            # Determine relationship type
            from_card = str(rel['From Cardinality'])
            to_card = str(rel['To Cardinality'])
            
            if from_card == '2' and to_card == '1':
                rel_type = ">"  # many-to-one
            elif from_card == '1' and to_card == '2':
                rel_type = "<"  # one-to-many
            elif from_card == '1' and to_card == '1':
                rel_type = "-"  # one-to-one
            else:
                rel_type = ">"  # default to many-to-one
            
            # Add relationship
            rel_line = f"Ref: {from_table}.{from_col} {rel_type} {to_table}.{to_col}"
            
            # Add cross-filter direction as note
            cross_filter = rel['Cross Filter Direction']
            if pd.notna(cross_filter):
                rel_line += f" [note: 'Cross-filter: {cross_filter}']"
            
            relationships.append(rel_line)
        
        return relationships
    
    def generate_glossary_excel(self, output_file='semantic_model_glossary.xlsx'):
        """Generate comprehensive glossary in Excel format with Semantic Model Name as first column"""
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Sheet 1: Tables Overview
            tables_summary = self._create_tables_summary()
            tables_summary.to_excel(writer, sheet_name='Tables Overview', index=False)
            
            # Sheet 2: All Columns
            columns_glossary = self._create_columns_glossary()
            columns_glossary.to_excel(writer, sheet_name='Columns Glossary', index=False)
            
            # Sheet 3: All Measures
            measures_glossary = self._create_measures_glossary()
            measures_glossary.to_excel(writer, sheet_name='Measures Glossary', index=False)
            
            # Sheet 4: Relationships (Enhanced with physical table/column info)
            relationships_enhanced = self._create_relationships_glossary()
            relationships_enhanced.to_excel(writer, sheet_name='Relationships', index=False)
            
            # Sheet 5: Data Lineage Summary
            lineage_summary = self._create_data_lineage_summary()
            lineage_summary.to_excel(writer, sheet_name='Data Lineage', index=False)
            
            # Sheet 6: Key Columns Summary
            key_columns = self._create_key_columns_summary()
            key_columns.to_excel(writer, sheet_name='Key Columns', index=False)
            
            # Sheet 7: Hidden Objects
            hidden_objects = self._create_hidden_objects_summary()
            hidden_objects.to_excel(writer, sheet_name='Hidden Objects', index=False)
            
            # Sheet 8: Model Summary Statistics
            model_stats = self._create_model_statistics()
            model_stats.to_excel(writer, sheet_name='Model Statistics', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        print(f"✅ Glossary Excel generated: {output_file}")
        return output_file
    
    def _create_tables_summary(self):
        """Create tables overview summary with Semantic Model Name as first column"""
        summary = []
        
        for table in self.columns_df['Table'].unique():
            table_data = self.columns_df[self.columns_df['Table'] == table]
            
            # Determine table type
            if table in self.fact_tables:
                table_type = "Fact"
            elif table in self.dim_tables:
                table_type = "Dimension"
            else:
                table_type = "Other"
            
            # Get physical table name from cache
            physical_table = self._physical_table_cache.get(table, '')
            
            # Count relationships
            outgoing_rels = len(self.relationships_df[self.relationships_df['From Table'] == table])
            incoming_rels = len(self.relationships_df[self.relationships_df['To Table'] == table])
            
            # Get related tables
            related_tables = self._get_related_tables(table)
            
            # Get key columns
            key_cols = table_data[table_data['Is Key'].astype(str).str.lower() == 'true']['Column'].tolist()
            
            # Get hidden column count
            hidden_cols = len(table_data[table_data['Is Hidden'].astype(str).str.lower() == 'true'])
            
            summary.append({
                'Semantic Model': self.semantic_model_name,
                'Table Name': table,
                'Table Type': table_type,
                'Physical/ETL Source Table': physical_table if physical_table else '',
                'Description': table_data['Table Description'].iloc[0] if not table_data.empty and pd.notna(table_data['Table Description'].iloc[0]) else '',
                'Column Count': len(table_data),
                'Key Columns': ', '.join(key_cols) if key_cols else '',
                'Hidden Columns': hidden_cols,
                'Storage Mode': table_data['Storage Mode'].iloc[0] if not table_data.empty and 'Storage Mode' in table_data.columns else '',
                'Outgoing Relationships': outgoing_rels,
                'Incoming Relationships': incoming_rels,
                'Related Tables': ', '.join(related_tables) if related_tables else ''
            })
        
        return pd.DataFrame(summary)
    
    def _create_columns_glossary(self):
        """Create detailed columns glossary with Semantic Model Name as first column and physical info"""
        glossary_data = []
        
        for _, row in self.columns_df.iterrows():
            table_name = row['Table']
            column_name = row['Column']
            
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
            
            # Check if this column is used in relationships
            is_relationship_key = self._is_column_in_relationship(table_name, column_name)
            
            glossary_data.append({
                'Semantic Model': self.semantic_model_name,
                'Table Type': table_type,
                'Table Name': table_name,
                'Column Name': column_name,
                'Physical/ETL Source Table': physical_table if physical_table else '',
                'Physical/ETL Source Column': physical_column if physical_column else '',
                'Column Description': row.get('Column Description', ''),
                'Data Type': row.get('Data Type', ''),
                'Column Type': row.get('Column Type', ''),
                'Is Key': row.get('Is Key', ''),
                'Is Hidden': row.get('Is Hidden', ''),
                'Is Relationship Key': 'Yes' if is_relationship_key else 'No',
                'Format String': row.get('Format String', ''),
                'Data Category': row.get('Data Category', ''),
                'Summarize By': row.get('Summarize By', ''),
                'Source Column': row.get('Source Column', ''),
                'Source Query/Expression': row.get('Source Query/Expression', '')
            })
        
        return pd.DataFrame(glossary_data)
    
    def _create_measures_glossary(self):
        """Create measures glossary with Semantic Model Name as first column and DAX explanations"""
        measures_data = []
        
        for _, row in self.measures_df.iterrows():
            table_name = row.get('Table', '')
            
            # Get referenced tables and columns from DAX
            dax_expr = row.get('DAX Expression', '')
            referenced_tables, referenced_columns = self._parse_dax_references(dax_expr)
            
            measures_data.append({
                'Semantic Model': self.semantic_model_name,
                'Table Name': table_name,
                'Measure Name': row.get('Measure', ''),
                'Description': row.get('Description', ''),
                'DAX Expression': dax_expr,
                'DAX Explanation': self._explain_dax(dax_expr),
                'Is Hidden': row.get('Is Hidden', ''),
                'Format String': row.get('Format String', ''),
                'Display Folder': row.get('Display Folder', ''),
                'Referenced Tables': ', '.join(referenced_tables) if referenced_tables else '',
                'Referenced Columns': ', '.join(referenced_columns) if referenced_columns else ''
            })
        
        return pd.DataFrame(measures_data)
    
    def _create_relationships_glossary(self):
        """Create enhanced relationships glossary with physical table/column info"""
        relationships_data = []
        
        for _, rel in self.relationships_df.iterrows():
            from_table = rel['From Table']
            from_column = rel['From Column']
            to_table = rel['To Table']
            to_column = rel['To Column']
            
            # Get physical table/column names from cache
            from_physical_table = self._physical_table_cache.get(from_table, '')
            from_physical_column = self._physical_column_cache.get((from_table, from_column), '')
            to_physical_table = self._physical_table_cache.get(to_table, '')
            to_physical_column = self._physical_column_cache.get((to_table, to_column), '')
            
            # Determine table types
            from_table_type = 'Fact' if from_table in self.fact_tables else ('Dimension' if from_table in self.dim_tables else 'Other')
            to_table_type = 'Fact' if to_table in self.fact_tables else ('Dimension' if to_table in self.dim_tables else 'Other')
            
            # Interpret cardinality
            from_card = str(rel.get('From Cardinality', ''))
            to_card = str(rel.get('To Cardinality', ''))
            cardinality_desc = self._interpret_cardinality(from_card, to_card)
            
            # Get cross-filter direction description
            cross_filter = rel.get('Cross Filter Direction', '')
            cross_filter_desc = self._interpret_cross_filter(cross_filter)
            
            relationships_data.append({
                'Semantic Model': self.semantic_model_name,
                'Relationship ID': rel.get('Relationship ID', ''),
                'From Table': from_table,
                'From Table Type': from_table_type,
                'From Column': from_column,
                'From Physical/ETL Source Table': from_physical_table if from_physical_table else '',
                'From Physical/ETL Source Column': from_physical_column if from_physical_column else '',
                'To Table': to_table,
                'To Table Type': to_table_type,
                'To Column': to_column,
                'To Physical/ETL Source Table': to_physical_table if to_physical_table else '',
                'To Physical/ETL Source Column': to_physical_column if to_physical_column else '',
                'From Cardinality': from_card,
                'To Cardinality': to_card,
                'Cardinality Description': cardinality_desc,
                'Cross Filter Direction': cross_filter,
                'Cross Filter Description': cross_filter_desc,
                'Is Active': rel.get('Is Active', ''),
                'Security Filtering': rel.get('Security Filtering', '')
            })
        
        return pd.DataFrame(relationships_data)
    
    def _create_data_lineage_summary(self):
        """Create a data lineage summary showing physical to semantic mapping"""
        lineage_data = []
        
        for _, row in self.columns_df.iterrows():
            table_name = row['Table']
            column_name = row['Column']
            
            # Get physical info
            physical_table = self._physical_table_cache.get(table_name, '')
            physical_column = self._physical_column_cache.get((table_name, column_name), '')
            
            # Only include rows with physical mapping
            if physical_table or physical_column:
                table_type = 'Fact' if table_name in self.fact_tables else ('Dimension' if table_name in self.dim_tables else 'Other')
                
                lineage_data.append({
                    'Semantic Model': self.semantic_model_name,
                    'Physical/ETL Source Table': physical_table if physical_table else table_name,
                    'Physical/ETL Source Column': physical_column if physical_column else column_name,
                    'Semantic Table': table_name,
                    'Semantic Column': column_name,
                    'Table Type': table_type,
                    'Data Type': row.get('Data Type', ''),
                    'Transformation': 'Direct Mapping' if (not physical_column or physical_column.lower() == column_name.lower()) else 'Column Renamed',
                    'Source Query/Expression': row.get('Source Query/Expression', '')
                })
        
        return pd.DataFrame(lineage_data)
    
    def _create_key_columns_summary(self):
        """Create a summary of all key columns used in relationships"""
        key_data = []
        
        # Get unique relationship columns
        relationship_cols = set()
        for _, rel in self.relationships_df.iterrows():
            relationship_cols.add((rel['From Table'], rel['From Column']))
            relationship_cols.add((rel['To Table'], rel['To Column']))
        
        for table_name, column_name in relationship_cols:
            # Get column details
            col_data = self.columns_df[
                (self.columns_df['Table'] == table_name) & 
                (self.columns_df['Column'] == column_name)
            ]
            
            if not col_data.empty:
                row = col_data.iloc[0]
                physical_table = self._physical_table_cache.get(table_name, '')
                physical_column = self._physical_column_cache.get((table_name, column_name), '')
                table_type = 'Fact' if table_name in self.fact_tables else ('Dimension' if table_name in self.dim_tables else 'Other')
                
                # Find related tables through this key
                related = []
                for _, rel in self.relationships_df.iterrows():
                    if rel['From Table'] == table_name and rel['From Column'] == column_name:
                        related.append(rel['To Table'])
                    elif rel['To Table'] == table_name and rel['To Column'] == column_name:
                        related.append(rel['From Table'])
                
                key_data.append({
                    'Semantic Model': self.semantic_model_name,
                    'Table Name': table_name,
                    'Table Type': table_type,
                    'Key Column': column_name,
                    'Physical/ETL Source Table': physical_table if physical_table else '',
                    'Physical/ETL Source Column': physical_column if physical_column else '',
                    'Data Type': row.get('Data Type', ''),
                    'Is Primary Key': row.get('Is Key', ''),
                    'Related Tables': ', '.join(related) if related else ''
                })
        
        return pd.DataFrame(key_data)
    
    def _create_hidden_objects_summary(self):
        """Create a summary of all hidden columns and measures"""
        hidden_data = []
        
        # Hidden columns
        hidden_cols = self.columns_df[self.columns_df['Is Hidden'].astype(str).str.lower() == 'true']
        for _, row in hidden_cols.iterrows():
            table_name = row['Table']
            column_name = row['Column']
            physical_table = self._physical_table_cache.get(table_name, '')
            physical_column = self._physical_column_cache.get((table_name, column_name), '')
            
            hidden_data.append({
                'Semantic Model': self.semantic_model_name,
                'Object Type': 'Column',
                'Table Name': table_name,
                'Object Name': column_name,
                'Physical/ETL Source Table': physical_table if physical_table else '',
                'Physical/ETL Source Column': physical_column if physical_column else '',
                'Description': row.get('Column Description', ''),
                'Reason for Hiding': 'Technical column / Not for end-user reporting'
            })
        
        # Hidden measures
        if 'Is Hidden' in self.measures_df.columns:
            hidden_measures = self.measures_df[self.measures_df['Is Hidden'].astype(str).str.lower() == 'true']
            for _, row in hidden_measures.iterrows():
                hidden_data.append({
                    'Semantic Model': self.semantic_model_name,
                    'Object Type': 'Measure',
                    'Table Name': row.get('Table', ''),
                    'Object Name': row.get('Measure', ''),
                    'Physical/ETL Source Table': '',
                    'Physical/ETL Source Column': '',
                    'Description': row.get('Description', ''),
                    'Reason for Hiding': 'Intermediate calculation / Not for end-user reporting'
                })
        
        return pd.DataFrame(hidden_data)
    
    def _create_model_statistics(self):
        """Create model-level statistics summary"""
        stats = []
        
        # Basic counts
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Tables',
            'Metric': 'Total Tables',
            'Value': len(self.columns_df['Table'].unique()),
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
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Columns',
            'Metric': 'Hidden Columns',
            'Value': len(self.columns_df[self.columns_df['Is Hidden'].astype(str).str.lower() == 'true']),
            'Details': ''
        })
        stats.append({
            'Semantic Model': self.semantic_model_name,
            'Category': 'Columns',
            'Metric': 'Key Columns',
            'Value': len(self.columns_df[self.columns_df['Is Key'].astype(str).str.lower() == 'true']),
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
        data_type_counts = self.columns_df['Data Type'].value_counts()
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
            storage_counts = self.columns_df.groupby('Table')['Storage Mode'].first().value_counts()
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
        
        # From relationships where this table is the source
        rels_out = self.relationships_df[self.relationships_df['From Table'] == table_name]
        related.update(rels_out['To Table'].unique())
        
        # From relationships where this table is the target
        rels_in = self.relationships_df[self.relationships_df['To Table'] == table_name]
        related.update(rels_in['From Table'].unique())
        
        return list(related)
    
    def _is_column_in_relationship(self, table_name, column_name):
        """Check if a column is used in any relationship"""
        from_match = ((self.relationships_df['From Table'] == table_name) & 
                      (self.relationships_df['From Column'] == column_name))
        to_match = ((self.relationships_df['To Table'] == table_name) & 
                    (self.relationships_df['To Column'] == column_name))
        return (from_match | to_match).any()
    
    def _parse_dax_references(self, dax_formula):
        """Parse DAX formula to extract referenced tables and columns"""
        if pd.isna(dax_formula):
            return [], []
        
        tables = set()
        columns = set()
        dax = str(dax_formula)
        
        # Pattern: 'Table Name'[Column Name] or Table[Column]
        import re
        
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
        if pd.isna(cross_filter):
            return ""
        
        cf = str(cross_filter).lower()
        if cf in ['1', 'single', 'onedirection']:
            return "Single direction - filters flow from 'One' side to 'Many' side"
        elif cf in ['2', 'both', 'bidirectional']:
            return "Bidirectional - filters flow in both directions"
        elif cf in ['3', 'automatic']:
            return "Automatic - Power BI determines filter direction"
        else:
            return str(cross_filter)
    
    def generate_mapping_excel(self, output_file='oracle_to_powerbi_mapping.xlsx'):
        """Generate Oracle to Power BI mapping document"""
        if self.mapping_df is None:
            print("⚠️  No mapping file provided. Skipping mapping generation.")
            return None
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Add Semantic Model name to mapping
            mapping_with_model = self.mapping_df.copy()
            mapping_with_model.insert(0, 'Semantic Model', self.semantic_model_name)
            
            # Main mapping
            mapping_with_model.to_excel(writer, sheet_name='Oracle to Power BI Mapping', index=False)
            
            # Summary by table
            summary = self._create_mapping_summary()
            summary.to_excel(writer, sheet_name='Mapping Summary', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        print(f"✅ Mapping Excel generated: {output_file}")
        return output_file
    
    def _create_mapping_summary(self):
        """Create mapping summary by table"""
        if self.mapping_df is None:
            return pd.DataFrame()
        
        summary = self.mapping_df.groupby('Oracle Presentation Table').agg({
            'Oracle Presentation Column': 'count',
            'FABRIC Physical Table': lambda x: x.nunique()
        }).reset_index()
        
        summary.columns = ['Oracle Table', 'Column Count', 'Mapped to Power BI Tables']
        summary.insert(0, 'Semantic Model', self.semantic_model_name)
        
        return summary
    
    def generate_er_diagram_mermaid(self, output_file='er_diagram.mmd'):
        """Generate Mermaid ER diagram code"""
        mermaid = [f"---"]
        mermaid.append(f"title: {self.semantic_model_name} - Star Schema")
        mermaid.append("---")
        mermaid.append("erDiagram")
        
        # Add fact tables
        for fact in self.fact_tables:
            related_dims = self._get_related_dimensions(fact)
            for dim in related_dims:
                # Get relationship details
                rel = self.relationships_df[
                    ((self.relationships_df['From Table'] == fact) & 
                     (self.relationships_df['To Table'] == dim)) |
                    ((self.relationships_df['From Table'] == dim) & 
                     (self.relationships_df['To Table'] == fact))
                ]
                
                if not rel.empty:
                    rel_row = rel.iloc[0]
                    from_card = rel_row['From Cardinality']
                    to_card = rel_row['To Cardinality']
                    
                    # Determine relationship notation
                    if from_card == '2' and to_card == '1':
                        notation = "}o--||"
                    elif from_card == '1' and to_card == '2':
                        notation = "||--o{"
                    else:
                        notation = "||--||"
                    
                    mermaid.append(f'    {self._sanitize_name(fact)} {notation} {self._sanitize_name(dim)} : "relates to"')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(mermaid))
        
        print(f"✅ Mermaid ER diagram generated: {output_file}")
        print(f"   You can visualize this at: https://mermaid.live/")
        return output_file
    
    def _get_related_dimensions(self, fact_table):
        """Get dimension tables related to a fact table"""
        dimensions = set()
        
        # From fact to dimensions
        rels_out = self.relationships_df[self.relationships_df['From Table'] == fact_table]
        dimensions.update(rels_out['To Table'].unique())
        
        # From dimensions to fact
        rels_in = self.relationships_df[self.relationships_df['To Table'] == fact_table]
        dimensions.update(rels_in['From Table'].unique())
        
        return list(dimensions)
    
    # Utility methods
    def _get_physical_table_name(self, table_name):
        """Get the physical source table name (uses cache)"""
        return self._physical_table_cache.get(table_name)
    
    def _get_physical_column_name(self, table_name, column_name):
        """Get physical column name (uses cache)"""
        return self._physical_column_cache.get((table_name, column_name))
    
    def _sanitize_name(self, name):
        """Sanitize table/column names for DBML"""
        if pd.isna(name):
            return "unknown"
        name = str(name).strip()
        # Replace spaces and special characters
        name = name.replace(' ', '_').replace('-', '_').replace('/', '_')
        # Remove invalid characters
        name = ''.join(c for c in name if c.isalnum() or c == '_')
        return name
    
    def _escape_string(self, s):
        """Escape strings for DBML notes"""
        if pd.isna(s):
            return ""
        return str(s).replace("'", "\\'").replace('\n', ' ').replace('\r', '')
    
    def _map_data_type(self, pbi_type):
        """Map Power BI data types to DBML types"""
        if pd.isna(pbi_type):
            return "varchar"
        
        type_map = {
            'Int64': 'bigint',
            'String': 'varchar',
            'Decimal': 'decimal',
            'Double': 'double',
            'DateTime': 'datetime',
            'Boolean': 'boolean',
            'Date': 'date'
        }
        
        return type_map.get(str(pbi_type), 'varchar')
    
    def _explain_dax(self, dax_formula):
        """Provide simple explanation for DAX formulas"""
        if pd.isna(dax_formula):
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
    
    def generate_all_documents(self, output_dir='output'):
        """Generate all documentation at once"""
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        print(f"🚀 Generating Power BI documentation for: {self.semantic_model_name}\n")
        
        # Generate DBML
        dbml_file = os.path.join(output_dir, 'semantic_model.dbml')
        self.generate_dbml(dbml_file)
        
        # Generate Glossary
        glossary_file = os.path.join(output_dir, 'semantic_model_glossary.xlsx')
        self.generate_glossary_excel(glossary_file)
        
        # Generate Mapping (if available)
        if self.mapping_df is not None:
            mapping_file = os.path.join(output_dir, 'oracle_to_powerbi_mapping.xlsx')
            self.generate_mapping_excel(mapping_file)
        
        # Generate ER Diagram (Mermaid)
        er_file = os.path.join(output_dir, 'er_diagram.mmd')
        self.generate_er_diagram_mermaid(er_file)
        
        print("\n✅ All documents generated successfully!")
        print(f"📁 Output directory: {output_dir}")
        print(f"\n📊 Semantic Model: {self.semantic_model_name}")
        print("\n📋 Generated files:")
        print(f"   1. {dbml_file} - DBML schema with star schema layout")
        print(f"   2. {glossary_file} - Complete glossary with:")
        print(f"      • Tables Overview (with physical source tables)")
        print(f"      • Columns Glossary (with physical source columns)")
        print(f"      • Measures Glossary (with DAX explanations)")
        print(f"      • Relationships (with ETL source table/column info)")
        print(f"      • Data Lineage (physical to semantic mapping)")
        print(f"      • Key Columns (relationship keys summary)")
        print(f"      • Hidden Objects (hidden columns and measures)")
        print(f"      • Model Statistics (summary metrics)")
        if self.mapping_df is not None:
            print(f"   3. {mapping_file} - Oracle to Power BI mapping")
        print(f"   4. {er_file} - Mermaid ER diagram (visualize at mermaid.live)")


# Example usage
if __name__ == "__main__":
    # Get the current working directory (where you're running the script from)
    current_directory = os.getcwd()
    
    print(f"📁 Current working directory: {current_directory}")
    print(f"📂 Looking for files in: {current_directory}\n")
    
    # Define file paths - UPDATE THESE WITH YOUR ACTUAL FILENAMES
    columns_file = os.path.join(current_directory, 'SemanticModelName_COLUMNS.csv')
    measures_file = os.path.join(current_directory, 'SemanticModelName_MEASURES.csv')
    relationships_file = os.path.join(current_directory, 'SemanticModelName_RELATIONSHIPS.csv')
    mapping_file = os.path.join(current_directory, 'RPDtoPBI_Mapping_Draft.xlsx')  # Optional
    
    # Optional: Specify semantic model name explicitly
    # If not provided, it will be derived from the columns file name
    semantic_model_name = None  # e.g., "Sales Analytics Model"
    
    # Check if files exist before proceeding
    files_to_check = {
        'Columns': columns_file,
        'Measures': measures_file,
        'Relationships': relationships_file,
        'Mapping': mapping_file
    }
    
    missing_files = []
    for file_type, file_path in files_to_check.items():
        if os.path.exists(file_path):
            print(f"✅ Found {file_type} file: {os.path.basename(file_path)}")
        else:
            print(f"❌ Missing {file_type} file: {os.path.basename(file_path)}")
            missing_files.append(file_type)
    
    # If critical files are missing, show available files and exit
    if 'Columns' in missing_files or 'Measures' in missing_files or 'Relationships' in missing_files:
        print(f"\n⚠️  Critical files are missing. Please check your file names.")
        print(f"\n📋 Available CSV/XLSX files in current directory:")
        for file in os.listdir(current_directory):
            if file.endswith(('.csv', '.xlsx')):
                print(f"   - {file}")
        print(f"\n💡 Update the file names in the script to match your actual files.")
        exit(1)
    
    # Set mapping_file to None if it doesn't exist
    if 'Mapping' in missing_files:
        mapping_file = None
        print(f"\nℹ️  Mapping file not found. Will skip mapping generation.\n")
    
    # Initialize generator
    try:
        generator = PowerBIDocumentationGenerator(
            columns_file=columns_file,
            measures_file=measures_file,
            relationships_file=relationships_file,
            mapping_file=mapping_file,
            semantic_model_name=semantic_model_name  # Optional: pass explicit name
        )
        
        # Generate all documents
        generator.generate_all_documents(output_dir='powerbi_documentation')
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
