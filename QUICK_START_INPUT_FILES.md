# Quick Start: Using Input Files

## 3 Simple Steps

### 1. Prepare Your Data Files

Create three files in a folder (e.g., `my_reservoir/`):

**`pvt.csv`** - Your PVT data
```csv
pressure,Bo,Rs,Bg,Bw,cw,cf
3330,1.25,510,0.00087,1.02,3e-6,4e-6
3000,1.22,450,0.00096,1.02,3e-6,4e-6
2700,1.20,401,0.00107,1.02,3e-6,4e-6
```

**`production.csv`** - Your production history
```csv
time,Np,Gp,Wp,pressure
0,0,0,0,3330
365,3000000,3000000000,0,3000
730,6000000,6000000000,0,2700
```

**`config.json`** - Your reservoir parameters
```json
{
  "unit_system": "FIELD",
  "reservoir_type": "oil",
  "initial_pressure": 3330,
  "reservoir_temperature": 180,
  "m": 0.5
}
```

### 2. Create Python Script

Create `analyze.py`:

```python
from material_balance import InputReader

# Load all data from files
reservoir, production = InputReader.create_oil_reservoir_from_files(
    pvt_file='my_reservoir/pvt.csv',
    production_file='my_reservoir/production.csv',
    config_file='my_reservoir/config.json'
)

# Calculate STOIIP
stoiip_values, stats = reservoir.calculate_STOIIP_from_production_data(production)

# Print results
print(f"Mean STOIIP: {stats['mean']/1e6:.2f} million m³")
print(f"Range: {stats['min']/1e6:.2f} - {stats['max']/1e6:.2f} million m³")
print(f"Valid calculations: {stats['count']} points")
```

### 3. Run Analysis

```bash
python analyze.py
```

## That's it!

Now you can:
- Edit your CSV files in Excel
- Update parameters in the JSON file  
- Re-run the analysis anytime

No Python code changes needed!

---

**Need templates?** Run this to generate example files:

```python
from material_balance import create_template_files, UnitSystem

create_template_files(output_dir='templates', unit_system=UnitSystem.FIELD)
```

**Full documentation:** See `INPUT_FILES_GUIDE.md`

**Working example:** Run `python examples/example_from_files.py`
