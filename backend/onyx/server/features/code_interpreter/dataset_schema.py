import os
import sys
import traceback
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# Set up logging
import logging
logger = logging.getLogger("dataset_schema")

def extract_csv_schema(file_path: str) -> Tuple[List[str], Dict[str, str], List[Dict[str, Any]]]:
    """
    Extract the schema (column names and data types) from a CSV file
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Tuple containing:
        - List of column names
        - Dictionary mapping column names to data types
        - List of sample rows (up to 5)
    """
    try:
        # First check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return [], {}, []
            
        # Use pandas to infer data types and extract schema
        logger.info(f"Reading schema for: {file_path}")
        df = pd.read_csv(file_path, nrows=10)  # Read just a few rows to infer schema
        
        # Get column names
        columns = list(df.columns)
        
        # Infer data types
        dtype_mapping = {
            'int64': 'integer',
            'float64': 'float',
            'object': 'string',
            'bool': 'boolean',
            'datetime64': 'datetime',
            'category': 'category',
            'timedelta[ns]': 'timedelta'
        }
        
        # Map pandas dtypes to more readable types
        dtypes = {}
        for col in columns:
            pandas_dtype = str(df[col].dtype)
            readable_type = dtype_mapping.get(pandas_dtype, pandas_dtype)
            dtypes[col] = readable_type
            
        # Get a few sample rows as dictionaries
        sample_rows = df.head(5).to_dict('records')
        
        logger.info(f"Extracted schema with {len(columns)} columns")
        return columns, dtypes, sample_rows
        
    except Exception as e:
        logger.error(f"Error extracting schema from {file_path}: {str(e)}")
        traceback.print_exc()
        return [], {}, []

def format_csv_schema_info(file_path: str, filename: str) -> str:
    """
    Format CSV schema information for the LLM prompt
    
    Args:
        file_path: Path to the CSV file
        filename: Display name of the file
        
    Returns:
        Formatted schema information as a string
    """
    schema_info = ""
    
    columns, dtypes, sample_rows = extract_csv_schema(file_path)
    
    if not columns:
        return schema_info
        
    # Add schema information
    schema_info += f"  Schema of {filename}:\n"
    
    # Display column names and types in a table-like format
    schema_info += f"  Columns ({len(columns)}):\n"
    for col, dtype in dtypes.items():
        schema_info += f"    - {col} ({dtype})\n"
    
    # Add a sample row preview
    if sample_rows:
        schema_info += f"  Sample data (first row):\n"
        sample = sample_rows[0]
        for col, value in sample.items():
            # Format the value based on its type
            if isinstance(value, str):
                formatted_value = f'"{value}"'
            else:
                formatted_value = str(value)
            schema_info += f"    - {col}: {formatted_value}\n"
    
    return schema_info

def generate_schema_examples(filename: str, relative_path: str, sandbox_path: str) -> str:
    """
    Generate code examples based on the schema of a CSV file
    
    Args:
        filename: Display name of the file
        relative_path: Path to use in the code examples
        sandbox_path: Actual path to the file for schema extraction
        
    Returns:
        Code examples as a string
    """
    examples = ""
    
    # Create variable name from filename (cleaned)
    var_name = os.path.splitext(filename)[0].lower()
    var_name = ''.join(c if c.isalnum() else '_' for c in var_name)
    
    # Get schema information
    columns, dtypes, _ = extract_csv_schema(sandbox_path)
    
    # Basic loading example
    examples += f"# Load CSV file\\n"
    examples += f"df_{var_name} = pd.read_csv(DATASETS_PATH + '/{filename}')\\n"
    examples += f"print(df_{var_name}.info())\\n"
    examples += f"print(df_{var_name}.head())\\n\\n"
    
    # Add schema-specific examples if we have columns
    if columns:
        # Add examples using actual column names
        examples += f"# Examples using the actual columns in {filename}:\\n"
        
        # Add example for summary statistics on numeric columns
        numeric_cols = [col for col, dtype in dtypes.items() if dtype in ('integer', 'float')]
        if numeric_cols:
            col = numeric_cols[0]
            examples += f"# Basic statistics for {col}\\n"
            examples += f"print(f'Mean {col}: {{df_{var_name}[\"{col}\"].mean()}}')\\n"
            examples += f"print(f'Max {col}: {{df_{var_name}[\"{col}\"].max()}}')\\n\\n"
        
        # Add example for grouping if we have multiple column types
        if len(columns) >= 2 and numeric_cols and len(numeric_cols) < len(columns):
            # Find a categorical column to group by
            cat_col = next((col for col in columns if col not in numeric_cols), columns[0])
            agg_col = numeric_cols[0] if numeric_cols else columns[0]
            
            examples += f"# Group by example\\n"
            examples += f"grouped = df_{var_name}.groupby('{cat_col}')['{agg_col}'].agg(['count', 'mean'])\\n"
            examples += f"print(grouped)\\n\\n"
        
        # Add filtering example
        if columns:
            col = columns[0]
            examples += f"# Filtering example\\n"
            examples += f"filtered = df_{var_name}[df_{var_name}['{col}'] == df_{var_name}['{col}'].iloc[0]]\\n"
            examples += f"print(f'Number of filtered rows: {{len(filtered)}}')\\n"
            examples += f"print(filtered.head())\\n\\n"
    
    # Final reminder about using print()
    examples += "# IMPORTANT: Always wrap all outputs in print() statements\\n"
    examples += "# CORRECT: print(df.head())    INCORRECT: df.head()\\n"
    
    return examples 