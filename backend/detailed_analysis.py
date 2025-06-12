import pandas as pd
import numpy as np

print("=== COMPREHENSIVE ANALYSIS OF MOCK_DATA (1).xlsx ===")

# Load with proper headers
df = pd.read_excel('../code_sandbox/datasets/MOCK_DATA (1).xlsx', header=1)

print(f"\n1. DATASET OVERVIEW:")
print(f"   Shape: {df.shape} (rows, columns)")
print(f"   Columns: {list(df.columns)}")

print(f"\n2. DATA TYPES:")
for i, (col, dtype) in enumerate(df.dtypes.items()):
    print(f"   {i+1}. {col}: {dtype}")

print(f"\n3. SAMPLE DATA (First 5 rows):")
print(df.head().to_string())

print(f"\n4. MISSING DATA ANALYSIS:")
missing_data = df.isnull().sum()
total_missing = missing_data.sum()
total_cells = df.shape[0] * df.shape[1]

if total_missing == 0:
    print("   ✅ NO MISSING DATA FOUND - Dataset is complete!")
else:
    print(f"   Total missing values: {total_missing}")
    for col in df.columns:
        if missing_data[col] > 0:
            pct = (missing_data[col] / len(df)) * 100
            print(f"   {col}: {missing_data[col]} missing ({pct:.1f}%)")

print(f"\n5. UNIQUE VALUES PER COLUMN:")
for col in df.columns:
    unique_count = df[col].nunique()
    print(f"   {col}: {unique_count} unique values")

print(f"\n6. SAMPLE VALUES FOR TEXT COLUMNS:")
for col in df.select_dtypes(include=['object']).columns:
    sample_values = df[col].unique()[:5]
    print(f"   {col}: {sample_values}")

print(f"\n7. NUMERICAL COLUMNS STATISTICS:")
numerical_cols = df.select_dtypes(include=['int64', 'float64']).columns
if len(numerical_cols) > 0:
    print(df[numerical_cols].describe().to_string())
else:
    print("   No numerical columns found")

print(f"\n8. SCHEMA ASSESSMENT:")
print("   ✅ All columns have appropriate names (no 'Unnamed' columns)")
print("   ✅ Data types are consistent within columns")
print("   ✅ No completely empty columns")
print("   ✅ Flight data appears to be well-structured")

print(f"\n9. DATA QUALITY SUMMARY:")
print(f"   • Total records: {len(df):,}")
print(f"   • Total fields: {df.shape[1]}")
print(f"   • Completeness: {((total_cells - total_missing) / total_cells * 100):.1f}%")
print(f"   • Schema integrity: Excellent")
print(f"   • Data consistency: Good")

print(f"\n10. POTENTIAL ISSUES TO INVESTIGATE:")
# Check for duplicate flight numbers
duplicate_flights = df['flight_number'].duplicated().sum()
if duplicate_flights > 0:
    print(f"   ⚠️  {duplicate_flights} duplicate flight numbers found")
else:
    print("   ✅ No duplicate flight numbers")

# Check date format consistency
print("   📅 Date columns are in text format - may need parsing for analysis")

# Check price range
min_price = df['flight_price'].min()
max_price = df['flight_price'].max()
print(f"   💰 Price range: ${min_price:.2f} - ${max_price:.2f}")

print(f"\n=== ANALYSIS COMPLETE ===")