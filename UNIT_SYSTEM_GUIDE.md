# Unit System Selection Guide

The Material Balance Framework now supports both **metric** and **field** (English) unit systems!

## Quick Start

Simply add `unit_system=UnitSystem.FIELD` or `unit_system=UnitSystem.METRIC` to your inputs:

```python
from material_balance import OilReservoir, PVTProperties, UnitSystem

# Use FIELD units (psia, STB, SCF, °F)
pvt = PVTProperties(
    pressure=[3000, 2800, 2600],  # psia
    Bo=[1.25, 1.24, 1.23],        # rb/STB
    Rs=[500, 480, 460],            # SCF/STB
    Bg=[0.0008, 0.00085, 0.0009],  # rb/SCF
    unit_system=UnitSystem.FIELD   # ← Specify unit system
)

reservoir = OilReservoir(
    pvt_properties=pvt,
    initial_pressure=3000,         # psia
    reservoir_temperature=180,     # °F
    unit_system=UnitSystem.FIELD   # ← Specify unit system
)
```

## Supported Unit Systems

### UnitSystem.METRIC (Default)
- **Pressure**: kgf/cm²
- **Oil/Water Volume**: m³ std
- **Gas Volume**: m³ std
- **Temperature**: °C (input), K (calculations)
- **Bo/Bw**: m³/m³ std
- **Bg**: m³/m³ std
- **Rs (GOR)**: m³/m³ std
- **Compressibility**: 1/(kgf/cm²)

### UnitSystem.FIELD
- **Pressure**: psia
- **Oil/Water Volume**: STB
- **Gas Volume**: SCF
- **Temperature**: °F (input), K (calculations)
- **Bo/Bw**: rb/STB
- **Bg**: rb/SCF
- **Rs (GOR)**: SCF/STB
- **Compressibility**: 1/psi

## Complete Examples

### Example 1: Oil Reservoir with Field Units

```python
from material_balance import OilReservoir, PVTProperties, UnitSystem
from material_balance.oil_reservoir import ProductionData

# PVT data in FIELD units
pvt = PVTProperties(
    pressure=[3000, 2800, 2600, 2400, 2200],  # psia
    Bo=[1.25, 1.24, 1.23, 1.22, 1.21],        # rb/STB
    Rs=[500, 480, 460, 440, 420],              # SCF/STB
    Bg=[0.0008, 0.00085, 0.0009, 0.00095, 0.001],  # rb/SCF
    Bw=[1.02] * 5,                             # rb/STB
    cw=[3e-6] * 5,                             # 1/psi
    cf=[4e-6] * 5,                             # 1/psi
    unit_system=UnitSystem.FIELD
)

# Initialize reservoir
oil_res = OilReservoir(
    pvt_properties=pvt,
    initial_pressure=3000,      # psia
    reservoir_temperature=180,  # °F
    m=0.2,
    unit_system=UnitSystem.FIELD
)

# Production data in FIELD units
prod_data = ProductionData(
    time=[0, 365, 730, 1095, 1460],
    Np=[0, 500e3, 1200e3, 2000e3, 2900e3],      # STB
    Gp=[0, 250e6, 600e6, 1000e6, 1450e6],       # SCF
    Wp=[0, 10e3, 25e3, 42e3, 61e3],             # STB
    pressure=[3000, 2800, 2600, 2400, 2200],    # psia
    unit_system=UnitSystem.FIELD
)

# Calculate STOIIP (results in m³ std internally)
N_values, stats = oil_res.calculate_STOIIP_from_production_data(prod_data)

# Convert to STB for display
mean_stb = stats['mean'] * 6.28981  # m³ to STB
print(f"STOIIP: {mean_stb:,.0f} STB ({mean_stb/1e6:.1f} MMSTB)")
```

### Example 2: Gas Reservoir with Metric Units

```python
from material_balance import GasReservoir, PVTProperties, UnitSystem
from material_balance.gas_reservoir import GasProductionData

# PVT data in METRIC units (default)
pvt = PVTProperties(
    pressure=[281, 267, 253, 239, 225],  # kgf/cm²
    Bg=[0.283, 0.301, 0.318, 0.336, 0.354],  # m³/m³ std
    z=[0.85, 0.84, 0.83, 0.82, 0.81],
    unit_system=UnitSystem.METRIC  # Can be omitted (default)
)

# Initialize gas reservoir
gas_res = GasReservoir(
    pvt_properties=pvt,
    initial_pressure=281,     # kgf/cm²
    reservoir_temperature=93, # °C
    unit_system=UnitSystem.METRIC
)

# Production data in METRIC units
prod_data = GasProductionData(
    time=[0, 365, 730, 1095, 1460],
    Gp=[0, 141.6e6, 339.6e6, 566e6, 820.6e6],  # m³ std
    Wp=[0, 0, 0, 0, 0],                         # m³ std
    pressure=[281, 267, 253, 239, 225],         # kgf/cm²
    unit_system=UnitSystem.METRIC
)

# Calculate GIIP
G_values, stats = gas_res.calculate_GIIP_from_production_data(prod_data)
print(f"GIIP: {stats['mean']/1e6:.0f} Mm³ std")
```

## How It Works

1. **Input Conversion**: When you specify a unit system, all input data is automatically converted to internal metric units
2. **Internal Calculations**: All calculations are performed using metric units (for consistency and accuracy)
3. **Output Conversion**: Results are returned in metric units - you can convert them to your preferred units for display

## Conversion Factors

The framework uses these conversion factors (accessible via `UnitConverter` class):

```python
from material_balance import UnitConverter

# Pressure
1 psia = 0.0703069 kgf/cm²
1 kgf/cm² = 14.2233 psia

# Volume
1 STB = 0.158987 m³ std
1 SCF = 0.0283168 m³ std
1 m³ std = 6.28981 STB
1 m³ std = 35.3147 SCF

# Temperature
K = (°F - 32) × 5/9 + 273.15
°C = K - 273.15

# GOR
1 SCF/STB = 0.178107 m³/m³ std
1 m³/m³ std = 5.61458 SCF/STB

# Compressibility
1/psi × 14.2233 = 1/(kgf/cm²)
```

## Benefits

- **Flexibility**: Work with the unit system familiar to your region/industry
- **Automatic**: No manual conversion needed - specify once and forget
- **Consistent**: Internal calculations always use consistent metric units
- **Transparent**: Clear documentation of units at every step

## Migration Guide

If you have existing code using metric units, no changes needed! The default is `UnitSystem.METRIC`:

```python
# These are equivalent:
pvt = PVTProperties(pressure=[210, 196, 182], Bo=[1.25, 1.24, 1.23])
pvt = PVTProperties(pressure=[210, 196, 182], Bo=[1.25, 1.24, 1.23], unit_system=UnitSystem.METRIC)
```

## Tips

1. **Be Consistent**: Use the same unit system for PVT, Reservoir, and ProductionData objects
2. **Document Units**: Always comment what units your data is in
3. **Convert Results**: Results are in metric - convert for display if needed
4. **Check Data**: Ensure your PVT data matches your specified unit system

## Need Help?

- See `examples/example_usage.py` for metric unit examples
- See `examples/example_field_units.py` for field unit examples
- Check `METRIC_UNITS.md` for detailed conversion information
