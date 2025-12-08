import pandas as pd
import os
from pathlib import Path
from collections import defaultdict

class PowerBIDocumentationGenerator:
    def __init__(self, columns_file, measures_file, relationships_file, mapping_file=None, semantic_model_name=None):
        """Initialize with CSV file paths"""
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
        
        # Set semantic model name - try to extract from filename or use provided/default
        if semantic_model_name:
            self.semantic_model_name = semantic_model_name
        else:
            # Try to extract from columns file name
            base_name = os.path.basename(columns_file)
            if '_COLUMNS.csv' in base_name:
                self.semantic_model_name = base_name.replace('_COLUMNS.csv', '')
            elif 'COLUMNS.csv' in base_name:
                self.semantic_model_name = base_name.replace('COLUMNS.csv', '').strip('_')
            else:
                self.semantic_model_name = 'Semantic Model'
        
        # Identify fact and dimension tables
        self.fact_tables = []
        self.dim_tables = []
        self._classify_tables()
    
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
        dbml_content.append("// Generated from metadata extraction")
        dbml_content.append("// Star Schema: Facts in center, Dimensions around them\n")
        
        # Project definition
        dbml_content.append("Project PowerBI_SemanticModel {")
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
        
        # Get physical table name from Source Query/Expression or Source Column
        physical_table = self._get_physical_table_name(table_name)
        
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
            
            # Add physical source info
            physical_col = self._get_physical_column_name(table_name, col['Column'])
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
        """Generate comprehensive glossary in Excel format"""
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
            
            # Sheet 4: Relationships
            relationships_glossary = self._create_relationships_glossary()
            relationships_glossary.to_excel(writer, sheet_name='Relationships', index=False)
            
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
        """Create tables overview summary with Semantic Model name and Physical Table Name"""
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
            
            # Get physical table name
            physical_table = self._get_physical_table_name(table)
            
            # Count relationships
            outgoing_rels = len(self.relationships_df[self.relationships_df['From Table'] == table])
            incoming_rels = len(self.relationships_df[self.relationships_df['To Table'] == table])
            
            # Get storage mode
            storage_mode = table_data['Storage Mode'].iloc[0] if 'Storage Mode' in table_data.columns and not table_data.empty else ''
            
            # Get table description
            table_desc = table_data['Table Description'].iloc[0] if 'Table Description' in table_data.columns and not table_data.empty else ''
            
            summary.append({
                'Semantic Model Name': self.semantic_model_name,
                'Table Name': table,
                'Physical Table Name': physical_table if physical_table else table,
                'ETL Source / Physical Table Name': physical_table if physical_table else '',
                'Table Type': table_type,
                'Description': table_desc,
                'Column Count': len(table_data),
                'Storage Mode': storage_mode,
                'Outgoing Relationships': outgoing_rels,
                'Incoming Relationships': incoming_rels,
                'Total Relationships': outgoing_rels + incoming_rels
            })
        
        return pd.DataFrame(summary)
    
    def _create_columns_glossary(self):
        """Create detailed columns glossary with Semantic Model name, Physical Table Name, and Physical Column Name"""
        glossary = []
        
        for _, row in self.columns_df.iterrows():
            table_name = row['Table']
            column_name = row['Column']
            
            # Get physical table and column names
            physical_table = self._get_physical_table_name(table_name)
            physical_column = self._get_physical_column_name(table_name, column_name)
            
            # Determine table type
            if table_name in self.fact_tables:
                table_type = 'Fact'
            elif table_name in self.dim_tables:
                table_type = 'Dimension'
            else:
                table_type = 'Other'
            
            glossary.append({
                'Semantic Model Name': self.semantic_model_name,
                'Table Name': table_name,
                'Physical Table Name': physical_table if physical_table else table_name,
                'Column': column_name,
                'Physical Column Name': physical_column if physical_column else column_name,
                'Column Description': row.get('Column Description', ''),
                'Data Type': row.get('Data Type', ''),
                'Column Type': row.get('Column Type', ''),
                'Table Type': table_type,
                'Is Hidden': row.get('Is Hidden', ''),
                'Is Key': row.get('Is Key', ''),
                'Format String': row.get('Format String', ''),
                'Data Category': row.get('Data Category', ''),
                'Summarize By': row.get('Summarize By', ''),
                'Source Column': row.get('Source Column', ''),
                'Source Query/Expression': row.get('Source Query/Expression', '')
            })
        
        return pd.DataFrame(glossary)
    
    def _create_measures_glossary(self):
        """Create measures glossary with DAX explanations and Semantic Model name"""
        measures = self.measures_df.copy()
        
        # Add Semantic Model Name as first column
        measures.insert(0, 'Semantic Model Name', self.semantic_model_name)
        
        # Add simplified DAX explanation
        if 'DAX Expression' in measures.columns:
            measures['DAX Explanation'] = measures['DAX Expression'].apply(self._explain_dax)
        
        # Add more details if available
        if 'Table' in measures.columns:
            # Add physical table name for each measure
            measures['Physical Table Name'] = measures['Table'].apply(
                lambda x: self._get_physical_table_name(x) if pd.notna(x) else ''
            )
        
        # Reorder columns to have Semantic Model Name first
        cols = ['Semantic Model Name'] + [c for c in measures.columns if c != 'Semantic Model Name']
        measures = measures[cols]
        
        return measures
    
    def _create_relationships_glossary(self):
        """Create enhanced relationships glossary with ETL Source / Physical Table Name and Physical Column Names"""
        relationships = []
        
        for _, rel in self.relationships_df.iterrows():
            from_table = rel['From Table']
            from_column = rel['From Column']
            to_table = rel['To Table']
            to_column = rel['To Column']
            
            # Get physical table names
            from_physical_table = self._get_physical_table_name(from_table)
            to_physical_table = self._get_physical_table_name(to_table)
            
            # Get physical column names
            from_physical_column = self._get_physical_column_name(from_table, from_column)
            to_physical_column = self._get_physical_column_name(to_table, to_column)
            
            relationships.append({
                'Semantic Model Name': self.semantic_model_name,
                'From Table': from_table,
                'From Table Physical Name': from_physical_table if from_physical_table else from_table,
                'ETL Source / Physical Table Name (From)': from_physical_table if from_physical_table else '',
                'From Column': from_column,
                'From Column Physical Name': from_physical_column if from_physical_column else from_column,
                'ETL Source & Physical Column Name (From)': from_physical_column if from_physical_column else '',
                'To Table': to_table,
                'To Table Physical Name': to_physical_table if to_physical_table else to_table,
                'ETL Source / Physical Table Name (To)': to_physical_table if to_physical_table else '',
                'To Column': to_column,
                'To Column Physical Name': to_physical_column if to_physical_column else to_column,
                'ETL Source & Physical Column Name (To)': to_physical_column if to_physical_column else '',
                'From Cardinality': rel.get('From Cardinality', ''),
                'To Cardinality': rel.get('To Cardinality', ''),
                'Cross Filter Direction': rel.get('Cross Filter Direction', ''),
                'Is Active': rel.get('Is Active', ''),
                'Relationship Name': rel.get('Relationship Name', '') if 'Relationship Name' in rel else ''
            })
        
        return pd.DataFrame(relationships)
    
    def generate_mapping_excel(self, output_file='oracle_to_powerbi_mapping.xlsx'):
        """Generate Oracle to Power BI mapping document"""
        if self.mapping_df is None:
            print("⚠️  No mapping file provided. Skipping mapping generation.")
            return None
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main mapping
            self.mapping_df.to_excel(writer, sheet_name='Oracle to Power BI Mapping', index=False)
            
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
        
        return summary
    
    def generate_er_diagram_mermaid(self, output_file='er_diagram.mmd'):
        """Generate Mermaid ER diagram code"""
        mermaid = ["erDiagram"]
        
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
        """Get the physical source table name from Source Query/Expression or Source Column"""
        table_cols = self.columns_df[self.columns_df['Table'] == table_name]
        
        if table_cols.empty:
            return None
        
        # First, try to extract from Source Query/Expression column
        if 'Source Query/Expression' in table_cols.columns:
            for _, row in table_cols.iterrows():
                source_query = row.get('Source Query/Expression', '')
                if pd.notna(source_query) and str(source_query).strip():
                    source_str = str(source_query).strip()
                    
                    # Pattern 1: Direct table name
                    if not any(keyword in source_str.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'JOIN']):
                        cleaned = source_str.replace('[', '').replace(']', '').replace('"', '').replace("'", '').strip()
                        if '.' in cleaned:
                            cleaned = cleaned.split('.')[-1]
                        if cleaned and cleaned.lower() != table_name.lower():
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
                            if table_part and table_part.lower() != table_name.lower():
                                return table_part
                        except:
                            pass
        
        # Fallback: Source Column field
        for _, row in table_cols.iterrows():
            source = row.get('Source Column', '')
            if pd.notna(source) and '[' in str(source) and ']' in str(source):
                try:
                    # Extract table name from [Table].[Column] format
                    source_str = str(source)
                    if '].[' in source_str:
                        physical_table = source_str.split('].[')[0].replace('[', '').replace(']', '').strip()
                        if physical_table and physical_table.lower() != table_name.lower():
                            return physical_table
                except:
                    pass
        
        return None
    
    def _get_physical_column_name(self, table_name, column_name):
        """Get physical column name from Source Column or Source Query/Expression field"""
        col_row = self.columns_df[
            (self.columns_df['Table'] == table_name) & 
            (self.columns_df['Column'] == column_name)
        ]
        
        if col_row.empty:
            return None
        
        # First try Source Column field
        source = col_row.iloc[0].get('Source Column', '')
        if pd.notna(source) and '[' in str(source):
            try:
                source_str = str(source)
                # Handle [Table].[Column] format
                if '].[' in source_str:
                    col_part = source_str.split('].[')[1].replace(']', '').strip()
                    if col_part and col_part.lower() != column_name.lower():
                        return col_part
                else:
                    # Just [Column] format
                    parts = source_str.split('[')
                    if len(parts) >= 2:
                        col_part = parts[-1].split(']')[0]
                        if col_part and col_part.lower() != column_name.lower():
                            return col_part
            except:
                pass
        
        # Fallback: Source Query/Expression
        source_query = col_row.iloc[0].get('Source Query/Expression', '')
        if pd.notna(source_query) and '[' in str(source_query):
            try:
                source_str = str(source_query)
                # Handle [Table].[Column] format
                if '].[' in source_str:
                    col_part = source_str.split('].[')[1].replace(']', '').strip()
                    if col_part and '.' not in col_part and col_part.lower() != column_name.lower():
                        return col_part
                else:
                    # Just [Column] format
                    parts = source_str.split('[')
                    if len(parts) >= 2:
                        col_part = parts[-1].split(']')[0]
                        if col_part and '.' not in col_part and col_part.lower() != column_name.lower():
                            return col_part
            except:
                pass
        
        return None
    
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
        
        if 'SUM(' in dax:
            return "Aggregation: Calculates sum of values"
        elif 'CALCULATE(' in dax:
            return "Context modification: Modifies filter context for calculation"
        elif 'SUMX(' in dax:
            return "Iterator: Row-by-row calculation and sum"
        elif 'DIVIDE(' in dax:
            return "Safe division: Handles division with error handling"
        elif 'COUNTROWS(' in dax:
            return "Count: Counts number of rows"
        elif 'AVERAGE(' in dax:
            return "Aggregation: Calculates average of values"
        else:
            return "Custom calculation"
    
    def generate_all_documents(self, output_dir='output'):
        """Generate all documentation at once"""
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        print("🚀 Generating Power BI documentation...\n")
        
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
        print("\n📊 Generated files:")
        print(f"   1. {dbml_file} - DBML schema with star schema layout")
        print(f"   2. {glossary_file} - Complete glossary with tables, columns, measures")
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
            mapping_file=mapping_file
        )
        
        # Generate all documents
        generator.generate_all_documents(output_dir='powerbi_documentation')
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
