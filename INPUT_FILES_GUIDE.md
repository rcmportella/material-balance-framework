# Input Files System - User Guide

## Overview

The Material Balance application now supports reading input data from external files (CSV and JSON) that can be easily edited by users outside the application. This allows for quick data updates without modifying Python code.

## File Structure

The input system uses three types of files:

1. **PVT Properties (CSV)** - Tabular PVT data
2. **Production History (CSV)** - Production data over time
3. **Configuration (JSON)** - Reservoir parameters and settings

## File Formats

### 1. PVT Properties File (CSV)

Contains pressure-dependent PVT properties in tabular format.

**Example: `dake_pvt.csv`**
```csv
pressure,Bo,Rs,Bg,Bw,cw,cf
3330,1.2511,510,0.00087,1.02,3e-6,4e-6
3150,1.2353,477,0.00092,1.02,3e-6,4e-6
3000,1.2222,450,0.00096,1.02,3e-6,4e-6
```

**Column Descriptions:**
- `pressure`: Reservoir pressure (psia for FIELD, kgf/cm² for METRIC)
- `Bo`: Oil formation volume factor (rb/STB for FIELD, m³/m³ for METRIC)
- `Rs`: Solution gas-oil ratio (SCF/STB for FIELD, m³/m³ for METRIC)
- `Bg`: Gas formation volume factor (rb/SCF for FIELD, m³/m³ for METRIC)
- `Bw`: Water formation volume factor (rb/STB for FIELD, m³/m³ for METRIC)
- `cw`: Water compressibility (1/psi for FIELD, 1/kgf/cm² for METRIC)
- `cf`: Formation compressibility (1/psi for FIELD, 1/kgf/cm² for METRIC)

**Optional columns:** `z` (gas compressibility factor), `co`, `cg`

### 2. Production History File (CSV)

Contains production data over time.

**Example: `dake_production.csv`**
```csv
time,Np,Gp,Wp,pressure
0,0,0,0,3330
365,3295000,3459750000,0,3150
730,5903000,6257180000,0,3000
```

**Column Descriptions:**
- `time`: Time (days)
- `Np`: Cumulative oil production (STB for FIELD, m³ for METRIC)
- `Gp`: Cumulative gas production (SCF for FIELD, m³ for METRIC)
- `Wp`: Cumulative water production (STB for FIELD, m³ for METRIC)
- `pressure`: Average reservoir pressure (psia for FIELD, kgf/cm² for METRIC)

For gas reservoirs, `Np` column can be omitted.

### 3. Configuration File (JSON)

Contains reservoir parameters and settings.

**Example: `dake_config.json`**
```json
{
  "_comment": "Dake example - Gas cap oil reservoir configuration",
  "unit_system": "FIELD",
  "reservoir_type": "oil",
  "initial_pressure": 3330,
  "reservoir_temperature": 180,
  "m": 0.54,
  "aquifer_influx": false
}
```

**Parameter Descriptions:**
- `unit_system`: Either `"FIELD"` or `"METRIC"`
- `reservoir_type`: Either `"oil"` or `"gas"`
- `initial_pressure`: Initial reservoir pressure
- `reservoir_temperature`: Reservoir temperature (°F for FIELD, °C for METRIC)
- `m`: Gas cap size ratio (optional, default 0)
- `aquifer_influx`: Whether to consider aquifer influx (optional, default false)

## How to Use

### Step 1: Create Template Files

Run the template generator to create example files:

```python
from material_balance import create_template_files, UnitSystem

# Create FIELD units templates
create_template_files(
    output_dir='input_templates/field_units',
    unit_system=UnitSystem.FIELD
)

# Create METRIC units templates
create_template_files(
    output_dir='input_templates/metric_units',
    unit_system=UnitSystem.METRIC
)
```

### Step 2: Edit Files with Your Data

1. **Edit CSV files:**
   - Open in Excel, Google Sheets, or any text editor
   - Replace example data with your reservoir data
   - Keep the header row intact
   - Save as CSV (Comma delimited)

2. **Edit JSON file:**
   - Open in any text editor (Notepad, VS Code, etc.)
   - Update the parameters for your reservoir
   - Make sure to maintain valid JSON syntax
   - Use `"FIELD"` or `"METRIC"` for unit_system

### Step 3: Load Data in Your Application

```python
from material_balance import InputReader

# Define file paths
pvt_file = 'input_data/my_pvt.csv'
production_file = 'input_data/my_production.csv'
config_file = 'input_data/my_config.json'

# Create reservoir and production objects
reservoir, production = InputReader.create_oil_reservoir_from_files(
    pvt_file=pvt_file,
    production_file=production_file,
    config_file=config_file
)

# Perform calculations
stoiip_values, stats = reservoir.calculate_STOIIP_from_production_data(production)

print(f"Mean STOIIP: {stats['mean']/1e6:.2f} Mm³ std")
```

## Complete Example

See `examples/example_from_files.py` for a complete working example:

```bash
python examples/example_from_files.py
```

## Tips and Best Practices

1. **CSV File Tips:**
   - Use scientific notation for small numbers: `3e-6` instead of `0.000003`
   - Ensure no extra commas at the end of rows
   - Keep consistent decimal places for clarity
   - Don't use thousands separators (use `3295000`, not `3,295,000`)

2. **JSON File Tips:**
   - Use double quotes for strings: `"FIELD"` not `'FIELD'`
   - Comments (lines starting with `_comment`) are ignored by the parser
   - Boolean values: `true` or `false` (lowercase, no quotes)
   - Numbers don't need quotes

3. **Unit System Consistency:**
   - All three files must use the same unit system
   - Specify the unit system in the JSON config file
   - The application automatically converts to internal metric units

4. **Data Validation:**
   - Pressure values in CSV files should be in descending order (typical for production)
   - All CSV rows should have the same number of columns
   - Required columns: `pressure` in PVT file, `pressure` in production file

5. **Error Handling:**
   - If the application can't find your files, check the file paths
   - If parsing fails, check for syntax errors in JSON or CSV format
   - Watch for typos in column names (case-sensitive)

## Directory Structure Recommendation

```
your_project/
├── input_data/
│   ├── reservoir1_pvt.csv
│   ├── reservoir1_production.csv
│   └── reservoir1_config.json
├── analysis_scripts/
│   └── analyze_reservoir1.py
└── results/
    ├── stoiip_results.csv
    └── production_analysis.csv
```

## Advanced Usage

### Reading Individual Files

You can also read files individually:

```python
from material_balance import InputReader, UnitSystem

# Read only PVT properties
pvt = InputReader.read_pvt_from_csv('my_pvt.csv', UnitSystem.FIELD)

# Read only production data
production = InputReader.read_production_from_csv(
    'my_production.csv', 
    UnitSystem.FIELD, 
    reservoir_type='oil'
)

# Read only configuration
config = InputReader.read_config_from_json('my_config.json')
```

### Creating Custom Workflows

You can combine file reading with programmatic parameters:

```python
# Read PVT from file
pvt = InputReader.read_pvt_from_csv('pvt.csv', UnitSystem.FIELD)

# Create reservoir with custom parameters
from material_balance import OilReservoir

reservoir = OilReservoir(
    pvt_properties=pvt,
    initial_pressure=3500,  # Custom value
    reservoir_temperature=200,
    m=0.3,
    unit_system=UnitSystem.FIELD
)
```

## Troubleshooting

**Problem:** `FileNotFoundError: PVT file not found`
- **Solution:** Check that the file path is correct and the file exists

**Problem:** `ValueError: CSV file must contain a 'pressure' column`
- **Solution:** Ensure your CSV has a header row with a 'pressure' column

**Problem:** `TypeError: OilReservoir.__init__() got an unexpected keyword argument`
- **Solution:** Check your JSON config file for unsupported parameters

**Problem:** `Warning: Could not calculate STOIIP at point 0`
- **Solution:** This is normal for the first data point (initial conditions). The calculation starts from point 1.

**Problem:** Incorrect results or unit conversion errors
- **Solution:** Verify that `unit_system` in your JSON config matches the actual units in your CSV files

## Support

For more examples and documentation, see:
- `examples/example_from_files.py` - Complete working example
- `examples/input_data/` - Example input files
- `UNIT_SYSTEM_GUIDE.md` - Unit system documentation
