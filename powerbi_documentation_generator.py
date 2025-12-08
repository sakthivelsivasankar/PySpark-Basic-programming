from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import pandas as pd


class PowerBIDocumentationGenerator:
    """Generate a rich documentation pack for a Power BI semantic model."""

    def __init__(
        self,
        columns_file: str,
        measures_file: str,
        relationships_file: str,
        mapping_file: Optional[str] = None,
        semantic_model_name: Optional[str] = None,
    ) -> None:
        self.columns_file = columns_file
        self.measures_file = measures_file
        self.relationships_file = relationships_file
        self.mapping_file = mapping_file

        self.columns_df = self._read_csv_with_fallback(columns_file)
        self.measures_df = self._read_csv_with_fallback(measures_file)
        self.relationships_df = self._read_csv_with_fallback(relationships_file)
        self.mapping_df = self._read_mapping_file(mapping_file)

        self.semantic_model_name = (
            semantic_model_name or self._infer_model_name(columns_file)
        )
        self._physical_table_cache: Dict[str, Optional[str]] = {}
        self._physical_column_cache: Dict[tuple, Optional[str]] = {}
        self.table_source_lookup = self._build_table_source_lookup()

        self.fact_tables: list[str] = []
        self.dim_tables: list[str] = []
        self._classify_tables()

    # ------------------------------------------------------------------ #
    # Initialization helpers
    # ------------------------------------------------------------------ #
    def _read_csv_with_fallback(self, file_path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="latin-1")

    def _read_mapping_file(self, mapping_file: Optional[str]) -> Optional[pd.DataFrame]:
        if not mapping_file:
            return None

        if mapping_file.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(mapping_file)

        try:
            return pd.read_csv(mapping_file, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(mapping_file, encoding="latin-1")

    def _infer_model_name(self, columns_file: str) -> str:
        stem = Path(columns_file).stem
        lowered = stem.lower()
        suffixes = ["_columns", "-columns", " columns"]
        for suffix in suffixes:
            if lowered.endswith(suffix):
                stem = stem[: -len(suffix)]
                break

        friendly = stem.replace("_", " ").replace("-", " ").strip()
        return friendly or "Semantic Model"

    def _match_column_name(self, available: list[str], candidates: list[str]) -> Optional[str]:
        normalized = [col.strip().lower() for col in available]
        for candidate in candidates:
            if candidate in normalized:
                idx = normalized.index(candidate)
                return available[idx]

        for idx, col in enumerate(available):
            cleaned = col.strip().lower().replace(" ", "")
            for candidate in candidates:
                if candidate.replace(" ", "") in cleaned:
                    return available[idx]
        return None

    def _build_table_source_lookup(self) -> Dict[str, str]:
        if self.mapping_df is None:
            return {}

        columns = list(self.mapping_df.columns)
        table_col = self._match_column_name(
            columns,
            [
                "power bi table",
                "pbi table",
                "semantic model table",
                "semantic table",
                "fabric table",
                "tabular table",
                "table name",
            ],
        )
        source_col = self._match_column_name(
            columns,
            [
                "etl source",
                "source table",
                "source physical table",
                "oracle presentation table",
                "fabric physical table",
                "physical table",
            ],
        )

        if not table_col or not source_col:
            return {}

        lookup: Dict[str, str] = {}
        for _, row in self.mapping_df[[table_col, source_col]].dropna(
            how="all"
        ).iterrows():
            table_value = str(row[table_col]).strip()
            source_value = str(row[source_col]).strip()
            if table_value:
                lookup.setdefault(table_value.lower(), source_value)

        return lookup

    def _classify_tables(self) -> None:
        tables = self.columns_df["Table"].dropna().unique()

        for table in tables:
            table_lower = table.lower()
            if any(prefix in table_lower for prefix in ["fact", "fact_", "fact -"]):
                self.fact_tables.append(table)
            elif any(prefix in table_lower for prefix in ["dim", "dim_", "dimension"]):
                self.dim_tables.append(table)
            else:
                outgoing = len(
                    self.relationships_df[
                        self.relationships_df["From Table"] == table
                    ]
                )
                incoming = len(
                    self.relationships_df[self.relationships_df["To Table"] == table]
                )
                if outgoing > incoming:
                    self.fact_tables.append(table)
                else:
                    self.dim_tables.append(table)

    # ------------------------------------------------------------------ #
    # DBML generation
    # ------------------------------------------------------------------ #
    def generate_dbml(self, output_file: str = "semantic_model.dbml") -> str:
        dbml_content = [
            "// Power BI Semantic Model - Star Schema",
            "// Generated from metadata extraction",
            "// Star Schema: Facts in center, Dimensions around them",
            "",
            "Project PowerBI_SemanticModel {",
            "  database_type: 'Power BI'",
            "  Note: 'Migrated from Oracle ADW/OBIEE to Microsoft Fabric'",
            "}",
            "",
            "// ===== FACT TABLES =====",
        ]

        for table in self.fact_tables:
            dbml_content.append(self._generate_table_dbml(table, is_fact=True))

        dbml_content.append("")
        dbml_content.append("// ===== DIMENSION TABLES =====")
        for table in self.dim_tables:
            dbml_content.append(self._generate_table_dbml(table))

        dbml_content.append("")
        dbml_content.append("// ===== RELATIONSHIPS =====")
        dbml_content.extend(self._generate_relationships_dbml())

        with open(output_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(dbml_content))

        print(f"✅ DBML file generated: {output_file}")
        return output_file

    def _generate_table_dbml(self, table_name: str, is_fact: bool = False) -> str:
        table_data = self.columns_df[self.columns_df["Table"] == table_name]
        if table_data.empty:
            return ""

        physical_table = self._get_physical_table_name(table_name)
        dbml = [f"\nTable {self._sanitize_name(table_name)} {{"]

        if physical_table and physical_table.lower() != table_name.lower():
            dbml.append(f"  // Physical/Source Table: {physical_table}")

        if "Table Description" in table_data.columns:
            table_desc = table_data["Table Description"].iloc[0]
            if pd.notna(table_desc):
                dbml.append(f"  Note: '{self._escape_string(table_desc)}'")

        for _, col in table_data.iterrows():
            column_name = self._sanitize_name(col["Column"])
            data_type = self._map_data_type(col.get("Data Type"))
            column_def = f"  {column_name} {data_type}"

            if str(col.get("Is Key", "")).lower() == "true":
                column_def += " [pk]"

            note_parts = []
            if pd.notna(col.get("Column Description")):
                note_parts.append(
                    self._escape_string(str(col.get("Column Description", "")))
                )

            physical_col = self._get_physical_column_name(table_name, col["Column"])
            if physical_col and physical_col.lower() != str(col["Column"]).lower():
                note_parts.append(f"Physical Column: {physical_col}")

            if physical_table and physical_table.lower() != table_name.lower():
                note_parts.append(f"Source Table: {physical_table}")

            if note_parts:
                column_def += f" [note: '{' | '.join(note_parts)}']"

            dbml.append(column_def)

        dbml.append("}")
        return "\n".join(dbml)

    def _generate_relationships_dbml(self) -> list[str]:
        relationships = []
        for _, rel in self.relationships_df.iterrows():
            from_table = self._sanitize_name(rel["From Table"])
            from_col = self._sanitize_name(rel["From Column"])
            to_table = self._sanitize_name(rel["To Table"])
            to_col = self._sanitize_name(rel["To Column"])

            from_card = str(rel.get("From Cardinality", ""))
            to_card = str(rel.get("To Cardinality", ""))

            if from_card == "2" and to_card == "1":
                relation = ">"
            elif from_card == "1" and to_card == "2":
                relation = "<"
            elif from_card == "1" and to_card == "1":
                relation = "-"
            else:
                relation = ">"

            rel_line = f"Ref: {from_table}.{from_col} {relation} {to_table}.{to_col}"

            cross_filter = rel.get("Cross Filter Direction")
            if pd.notna(cross_filter):
                rel_line += f" [note: 'Cross-filter: {cross_filter}']"

            relationships.append(rel_line)
        return relationships

    # ------------------------------------------------------------------ #
    # Glossary Excel generation
    # ------------------------------------------------------------------ #
    def generate_glossary_excel(self, output_file: str = "semantic_model_glossary.xlsx") -> str:
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            tables_summary = self._with_semantic_model_column(self._create_tables_summary())
            tables_summary.to_excel(writer, sheet_name="Tables Overview", index=False)

            columns_glossary = self._with_semantic_model_column(
                self._create_columns_glossary()
            )
            columns_glossary.to_excel(writer, sheet_name="Columns Glossary", index=False)

            measures_glossary = self._with_semantic_model_column(
                self._create_measures_glossary()
            )
            measures_glossary.to_excel(writer, sheet_name="Measures Glossary", index=False)

            relationships_glossary = self._with_semantic_model_column(
                self._create_relationships_glossary()
            )
            relationships_glossary.to_excel(writer, sheet_name="Relationships", index=False)

            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column_cells in worksheet.columns:
                    cells = list(column_cells)
                    max_length = 0
                    for cell in cells:
                        value = "" if cell.value is None else str(cell.value)
                        max_length = max(max_length, len(value))
                    worksheet.column_dimensions[cells[0].column_letter].width = min(
                        max_length + 2, 60
                    )

        print(f"✅ Glossary Excel generated: {output_file}")
        return output_file

    def _create_tables_summary(self) -> pd.DataFrame:
        summary_rows = []
        unique_tables = self.columns_df["Table"].dropna().unique()
        measure_table_col = "Table" if "Table" in self.measures_df.columns else None

        for table in unique_tables:
            table_data = self.columns_df[self.columns_df["Table"] == table]
            physical_table = self._get_physical_table_name(table) or ""
            etl_source = self._get_table_etl_source(table) or physical_table

            outgoing_rels = len(
                self.relationships_df[self.relationships_df["From Table"] == table]
            )
            incoming_rels = len(
                self.relationships_df[self.relationships_df["To Table"] == table]
            )
            key_columns = (
                table_data["Is Key"].astype(str).str.lower().eq("true").sum()
                if "Is Key" in table_data.columns
                else 0
            )
            hidden_columns = (
                table_data["Is Hidden"].astype(str).str.lower().eq("true").sum()
                if "Is Hidden" in table_data.columns
                else 0
            )
            measure_count = (
                len(self.measures_df[self.measures_df[measure_table_col] == table])
                if measure_table_col and not self.measures_df.empty
                else 0
            )

            summary_rows.append(
                {
                    "Table Name": table,
                    "Physical Table Name": physical_table,
                    "ETL Source": etl_source or "",
                    "Table Type": (
                        "Fact"
                        if table in self.fact_tables
                        else ("Dimension" if table in self.dim_tables else "Other")
                    ),
                    "Description": table_data["Table Description"].iloc[0]
                    if "Table Description" in table_data.columns and not table_data.empty
                    else "",
                    "Storage Mode": table_data["Storage Mode"].iloc[0]
                    if "Storage Mode" in table_data.columns and not table_data.empty
                    else "",
                    "Column Count": len(table_data),
                    "Key Columns": key_columns,
                    "Hidden Columns": hidden_columns,
                    "Measure Count": measure_count,
                    "Outgoing Relationships": outgoing_rels,
                    "Incoming Relationships": incoming_rels,
                }
            )

        return pd.DataFrame(summary_rows)

    def _create_columns_glossary(self) -> pd.DataFrame:
        required_columns = [
            "Table",
            "Column",
            "Column Description",
            "Data Type",
            "Column Type",
            "Is Hidden",
            "Is Key",
            "Format String",
            "Data Category",
            "Summarize By",
            "Source Column",
        ]
        existing_columns = [col for col in required_columns if col in self.columns_df.columns]
        glossary = self.columns_df[existing_columns].copy()
        if "Table" not in glossary.columns or "Column" not in glossary.columns:
            return glossary

        glossary["Table Type"] = glossary["Table"].apply(
            lambda val: "Fact"
            if val in self.fact_tables
            else ("Dimension" if val in self.dim_tables else "Other")
        )
        glossary["Physical Table Name"] = glossary["Table"].apply(
            lambda val: self._get_physical_table_name(val) or ""
        )
        glossary["Physical Column Name"] = glossary.apply(
            lambda row: self._get_physical_column_name(row["Table"], row["Column"]) or "",
            axis=1,
        )
        glossary["ETL Source"] = glossary.apply(
            lambda row: self._get_table_etl_source(row["Table"])
            or row["Physical Table Name"]
            or "",
            axis=1,
        )

        desired_order = [
            "Table Type",
            "Table",
            "Physical Table Name",
            "ETL Source",
            "Column",
            "Physical Column Name",
            "Column Description",
            "Data Type",
            "Column Type",
            "Is Hidden",
            "Is Key",
            "Format String",
            "Data Category",
            "Summarize By",
            "Source Column",
        ]

        available_order = [col for col in desired_order if col in glossary.columns]
        return glossary[available_order]

    def _create_measures_glossary(self) -> pd.DataFrame:
        measures = self.measures_df.copy()
        if measures.empty:
            return measures

        if "DAX Expression" in measures.columns:
            measures["DAX Explanation"] = measures["DAX Expression"].apply(
                self._explain_dax
            )
        else:
            measures["DAX Explanation"] = ""

        if "Table" in measures.columns:
            measures["Table Physical Name"] = measures["Table"].apply(
                lambda val: self._get_physical_table_name(val) or ""
            )
            measures["Table ETL Source"] = measures["Table"].apply(
                lambda val: self._get_table_etl_source(val)
                or self._get_physical_table_name(val)
                or ""
            )

        return measures

    def _create_relationships_glossary(self) -> pd.DataFrame:
        glossary = self.relationships_df.copy()
        glossary["From Physical Table"] = glossary["From Table"].apply(
            lambda val: self._get_physical_table_name(val) or ""
        )
        glossary["To Physical Table"] = glossary["To Table"].apply(
            lambda val: self._get_physical_table_name(val) or ""
        )
        glossary["From Physical Column"] = glossary.apply(
            lambda row: self._get_physical_column_name(row["From Table"], row["From Column"])
            or "",
            axis=1,
        )
        glossary["To Physical Column"] = glossary.apply(
            lambda row: self._get_physical_column_name(row["To Table"], row["To Column"])
            or "",
            axis=1,
        )
        glossary["From ETL Source"] = glossary["From Table"].apply(
            lambda val: self._get_table_etl_source(val)
            or self._get_physical_table_name(val)
            or ""
        )
        glossary["To ETL Source"] = glossary["To Table"].apply(
            lambda val: self._get_table_etl_source(val)
            or self._get_physical_table_name(val)
            or ""
        )

        desired_order = [
            "From Table",
            "From Physical Table",
            "From ETL Source",
            "From Column",
            "From Physical Column",
            "From Cardinality",
            "To Table",
            "To Physical Table",
            "To ETL Source",
            "To Column",
            "To Physical Column",
            "To Cardinality",
            "Is Active",
            "Cross Filter Direction",
            "Security Filtering Behavior",
        ]

        column_order = [col for col in desired_order if col in glossary.columns]
        column_order.extend(
            [col for col in glossary.columns if col not in column_order]
        )
        return glossary[column_order]

    # ------------------------------------------------------------------ #
    # Mapping Excel generation
    # ------------------------------------------------------------------ #
    def generate_mapping_excel(self, output_file: str = "oracle_to_powerbi_mapping.xlsx") -> Optional[str]:
        if self.mapping_df is None:
            print("⚠️  No mapping file provided. Skipping mapping generation.")
            return None

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            self.mapping_df.to_excel(
                writer, sheet_name="Oracle to Power BI Mapping", index=False
            )
            summary = self._create_mapping_summary()
            summary.to_excel(writer, sheet_name="Mapping Summary", index=False)

            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column_cells in worksheet.columns:
                    cells = list(column_cells)
                    max_length = 0
                    for cell in cells:
                        value = "" if cell.value is None else str(cell.value)
                        max_length = max(max_length, len(value))
                    worksheet.column_dimensions[cells[0].column_letter].width = min(
                        max_length + 2, 60
                    )

        print(f"✅ Mapping Excel generated: {output_file}")
        return output_file

    def _create_mapping_summary(self) -> pd.DataFrame:
        if self.mapping_df is None:
            return pd.DataFrame()

        if "Oracle Presentation Table" not in self.mapping_df.columns:
            return pd.DataFrame()

        agg_map: Dict[str, str | callable] = {}
        if "Oracle Presentation Column" in self.mapping_df.columns:
            agg_map["Oracle Presentation Column"] = "count"
        if "FABRIC Physical Table" in self.mapping_df.columns:
            agg_map["FABRIC Physical Table"] = pd.Series.nunique

        if not agg_map:
            return pd.DataFrame()

        summary = (
            self.mapping_df.groupby("Oracle Presentation Table")
            .agg(agg_map)
            .reset_index()
        )

        rename_map = {
            "Oracle Presentation Table": "Oracle Table",
            "Oracle Presentation Column": "Column Count",
            "FABRIC Physical Table": "Mapped to Power BI Tables",
        }
        return summary.rename(columns=rename_map)

    # ------------------------------------------------------------------ #
    # ER diagram helpers
    # ------------------------------------------------------------------ #
    def generate_er_diagram_mermaid(self, output_file: str = "er_diagram.mmd") -> str:
        mermaid_lines = ["erDiagram"]
        for fact_table in self.fact_tables:
            for dimension in self._get_related_dimensions(fact_table):
                relation = self.relationships_df[
                    ((self.relationships_df["From Table"] == fact_table) & (self.relationships_df["To Table"] == dimension))
                    | ((self.relationships_df["From Table"] == dimension) & (self.relationships_df["To Table"] == fact_table))
                ]
                if relation.empty:
                    continue

                rel_row = relation.iloc[0]
                from_card = rel_row.get("From Cardinality")
                to_card = rel_row.get("To Cardinality")
                if from_card == "2" and to_card == "1":
                    notation = "}o--||"
                elif from_card == "1" and to_card == "2":
                    notation = "||--o{"
                else:
                    notation = "||--||"

                mermaid_lines.append(
                    f"    {self._sanitize_name(fact_table)} {notation} {self._sanitize_name(dimension)} : relates to"
                )

        with open(output_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(mermaid_lines))

        print(f"✅ Mermaid ER diagram generated: {output_file}")
        print("   You can visualize this at: https://mermaid.live/")
        return output_file

    def _get_related_dimensions(self, fact_table: str) -> list[str]:
        related = set()
        outgoing = self.relationships_df[self.relationships_df["From Table"] == fact_table]
        incoming = self.relationships_df[self.relationships_df["To Table"] == fact_table]
        related.update(outgoing["To Table"].unique())
        related.update(incoming["From Table"].unique())
        return list(related)

    # ------------------------------------------------------------------ #
    # Metadata helpers
    # ------------------------------------------------------------------ #
    def _get_physical_table_name(self, table_name: str) -> Optional[str]:
        if not isinstance(table_name, str):
            return None

        if table_name in self._physical_table_cache:
            return self._physical_table_cache[table_name]

        table_data = self.columns_df[self.columns_df["Table"] == table_name]
        physical_name = None
        if table_data.empty:
            self._physical_table_cache[table_name] = None
            return None

        if "Source Query/Expression" in table_data.columns:
            for _, row in table_data.iterrows():
                source_query = row.get("Source Query/Expression")
                if pd.isna(source_query):
                    continue
                source_str = str(source_query).strip()
                if not source_str:
                    continue
                if not any(
                    keyword in source_str.upper()
                    for keyword in ["SELECT", "FROM", "WHERE", "JOIN"]
                ):
                    cleaned = (
                        source_str.replace("[", "")
                        .replace("]", "")
                        .replace('"', "")
                        .replace("'", "")
                        .strip()
                    )
                    if "." in cleaned:
                        cleaned = cleaned.split(".")[-1]
                    if cleaned and cleaned.lower() != table_name.lower():
                        physical_name = cleaned
                        break

                source_upper = source_str.upper()
                if "FROM" in source_upper:
                    from_idx = source_upper.find("FROM")
                    after_from = source_str[from_idx + 4 :].strip()
                    table_part = after_from.split()[0] if after_from.split() else ""
                    table_part = (
                        table_part.replace("[", "")
                        .replace("]", "")
                        .replace('"', "")
                        .replace("'", "")
                        .replace(",", "")
                        .strip()
                    )
                    if "." in table_part:
                        table_part = table_part.split(".")[-1]
                    if table_part and table_part.lower() != table_name.lower():
                        physical_name = table_part
                        break

        if physical_name is None:
            for _, row in table_data.iterrows():
                source = row.get("Source Column")
                if pd.isna(source) or "[" not in str(source):
                    continue
                try:
                    physical_table = str(source).split("[")[1].split("]")[0]
                    if physical_table.lower() != table_name.lower():
                        physical_name = physical_table
                        break
                except (IndexError, ValueError):
                    continue

        self._physical_table_cache[table_name] = physical_name
        return physical_name

    def _get_table_etl_source(self, table_name: str) -> Optional[str]:
        if not isinstance(table_name, str):
            return None
        lookup_key = table_name.lower()
        if lookup_key in self.table_source_lookup:
            return self.table_source_lookup[lookup_key]
        return self._get_physical_table_name(table_name)

    def _get_physical_column_name(self, table_name: str, column_name: str) -> Optional[str]:
        if not isinstance(table_name, str) or not isinstance(column_name, str):
            return None

        cache_key = (table_name, column_name)
        if cache_key in self._physical_column_cache:
            return self._physical_column_cache[cache_key]

        col_row = self.columns_df[
            (self.columns_df["Table"] == table_name)
            & (self.columns_df["Column"] == column_name)
        ]
        if col_row.empty:
            self._physical_column_cache[cache_key] = None
            return None

        source_column = col_row.iloc[0].get("Source Column", "")
        if pd.notna(source_column) and "[" in str(source_column):
            try:
                parts = str(source_column).split("[")
                candidate = parts[-1].split("]")[0]
                if candidate and candidate.lower() != column_name.lower():
                    self._physical_column_cache[cache_key] = candidate
                    return candidate
            except (IndexError, ValueError):
                pass

        source_query = col_row.iloc[0].get("Source Query/Expression", "")
        if pd.notna(source_query) and "[" in str(source_query):
            try:
                parts = str(source_query).split("[")
                candidate = parts[-1].split("]")[0]
                if (
                    candidate
                    and "." not in candidate
                    and candidate.lower() != column_name.lower()
                ):
                    self._physical_column_cache[cache_key] = candidate
                    return candidate
            except (IndexError, ValueError):
                pass

        self._physical_column_cache[cache_key] = None
        return None

    def _sanitize_name(self, name: str) -> str:
        if pd.isna(name):
            return "unknown"
        name = str(name).strip()
        name = (
            name.replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )
        return "".join(ch for ch in name if ch.isalnum() or ch == "_")

    def _escape_string(self, value: str) -> str:
        if pd.isna(value):
            return ""
        return str(value).replace("'", "\\'").replace("\n", " ").replace("\r", "")

    def _map_data_type(self, pbi_type: Optional[str]) -> str:
        if pd.isna(pbi_type):
            return "varchar"
        type_map = {
            "Int64": "bigint",
            "String": "varchar",
            "Decimal": "decimal",
            "Double": "double",
            "DateTime": "datetime",
            "Boolean": "boolean",
            "Date": "date",
        }
        return type_map.get(str(pbi_type), "varchar")

    def _explain_dax(self, dax_formula: Optional[str]) -> str:
        if pd.isna(dax_formula):
            return ""
        dax = str(dax_formula).upper()
        if "SUM(" in dax:
            return "Aggregation: Calculates sum of values"
        if "CALCULATE(" in dax:
            return "Context modification: Modifies filter context for calculation"
        if "SUMX(" in dax:
            return "Iterator: Row-by-row calculation and sum"
        if "DIVIDE(" in dax:
            return "Safe division: Handles division with error handling"
        if "COUNTROWS(" in dax:
            return "Count: Counts number of rows"
        if "AVERAGE(" in dax:
            return "Aggregation: Calculates average of values"
        return "Custom calculation"

    def _with_semantic_model_column(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df_copy = dataframe.copy()
        if "Semantic Model" in df_copy.columns:
            df_copy.drop(columns=["Semantic Model"], inplace=True)
        df_copy.insert(0, "Semantic Model", self.semantic_model_name)
        return df_copy

    # ------------------------------------------------------------------ #
    # Orchestration helper
    # ------------------------------------------------------------------ #
    def generate_all_documents(self, output_dir: str = "output") -> None:
        Path(output_dir).mkdir(exist_ok=True)

        print("🚀 Generating Power BI documentation...\n")

        dbml_file = os.path.join(output_dir, "semantic_model.dbml")
        self.generate_dbml(dbml_file)

        glossary_file = os.path.join(output_dir, "semantic_model_glossary.xlsx")
        self.generate_glossary_excel(glossary_file)

        if self.mapping_df is not None:
            mapping_file = os.path.join(output_dir, "oracle_to_powerbi_mapping.xlsx")
            self.generate_mapping_excel(mapping_file)

        er_file = os.path.join(output_dir, "er_diagram.mmd")
        self.generate_er_diagram_mermaid(er_file)

        print("\n✅ All documents generated successfully!")
        print(f"📁 Output directory: {output_dir}")
        print("\n📊 Generated files:")
        print(f"   1. {dbml_file} - DBML schema with star schema layout")
        print(f"   2. {glossary_file} - Complete glossary with tables, columns, measures")
        if self.mapping_df is not None:
            print(f"   3. {mapping_file} - Oracle to Power BI mapping")
        print(f"   4. {er_file} - Mermaid ER diagram (visualize at mermaid.live)")


if __name__ == "__main__":
    current_directory = os.getcwd()
    print(f"📁 Current working directory: {current_directory}")
    print(f"📂 Looking for files in: {current_directory}\n")

    columns_file = os.path.join(current_directory, "SemanticModelName_COLUMNS.csv")
    measures_file = os.path.join(current_directory, "SemanticModelName_MEASURES.csv")
    relationships_file = os.path.join(current_directory, "SemanticModelName_RELATIONSHIPS.csv")
    mapping_file = os.path.join(current_directory, "RPDtoPBI_Mapping_Draft.xlsx")

    files_to_check = {
        "Columns": columns_file,
        "Measures": measures_file,
        "Relationships": relationships_file,
        "Mapping": mapping_file,
    }

    missing_files = []
    for file_type, file_path in files_to_check.items():
        if os.path.exists(file_path):
            print(f"✅ Found {file_type} file: {os.path.basename(file_path)}")
        else:
            print(f"❌ Missing {file_type} file: {os.path.basename(file_path)}")
            missing_files.append(file_type)

    if "Columns" in missing_files or "Measures" in missing_files or "Relationships" in missing_files:
        print("\n⚠️  Critical files are missing. Please check your file names.")
        print("\n📋 Available CSV/XLSX files in current directory:")
        for file in os.listdir(current_directory):
            if file.endswith((".csv", ".xlsx")):
                print(f"   - {file}")
        print("\n💡 Update the file names in the script to match your actual files.")
        raise SystemExit(1)

    if "Mapping" in missing_files:
        mapping_file = None
        print("\nℹ️  Mapping file not found. Will skip mapping generation.\n")

    semantic_model_name = Path(columns_file).stem
    generator = PowerBIDocumentationGenerator(
        columns_file=columns_file,
        measures_file=measures_file,
        relationships_file=relationships_file,
        mapping_file=mapping_file,
        semantic_model_name=semantic_model_name,
    )

    try:
        generator.generate_all_documents(output_dir="powerbi_documentation")
    except Exception as error:
        print(f"\n❌ Error occurred: {error}")
        import traceback

        traceback.print_exc()
