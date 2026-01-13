# Unit System Feature - Implementation Summary

## Overview

The Material Balance Framework now supports **both metric and field (English) unit systems** with automatic conversion. Users can input data in their preferred unit system, and the framework handles all conversions internally.

## What Was Added

### 1. New Module: `units.py`
- **`UnitSystem`** enum: `METRIC` and `FIELD`
- **`UnitConverter`** class: Handles all unit conversions
  - Pressure (psia ↔ kgf/cm²)
  - Volume (STB/SCF ↔ m³ std)
  - Temperature (°F ↔ K ↔ °C)
  - Formation volume factors (rb/STB, rb/SCF ↔ m³/m³ std)
  - Gas-oil ratio (SCF/STB ↔ m³/m³ std)
  - Compressibility (1/psi ↔ 1/(kgf/cm²))

### 2. Updated Classes

#### `PVTProperties`
- Added `unit_system` parameter (default: `UnitSystem.METRIC`)
- Automatically converts all input data to internal metric units
- Supports both unit systems for all properties

#### `ProductionData` (Oil)
- Added `unit_system` parameter
- Converts Np, Gp, Wp, and pressure to metric units

#### `GasProductionData` (Gas)
- Added `unit_system` parameter
- Converts Gp, Wp, and pressure to metric units

#### `OilReservoir`
- Added `unit_system` parameter
- Converts initial_pressure and reservoir_temperature to metric units
- Stores `UnitConverter` instance for future use

#### `GasReservoir`
- Added `unit_system` parameter
- Converts initial_pressure and reservoir_temperature to metric units
- Stores `UnitConverter` instance for future use

### 3. Package Exports
- Updated `__init__.py` to export `UnitSystem` and `UnitConverter`

### 4. Documentation
- **`UNIT_SYSTEM_GUIDE.md`**: Complete guide with examples
- **`test_units.py`**: Unit tests verifying conversions work correctly
- **`examples/example_field_units.py`**: Full examples with field units

## How It Works

```
┌─────────────────┐
│  User Input     │
│  (Field Units)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  UnitConverter  │
│  Converts to    │
│  Metric         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Internal       │
│  Calculations   │
│  (Metric Units) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Results        │
│  (Metric Units) │
│  Can convert    │
│  for display    │
└─────────────────┘
```

## Usage Example

```python
from material_balance import OilReservoir, PVTProperties, UnitSystem

# Input in FIELD units
pvt = PVTProperties(
    pressure=[3000, 2800, 2600],  # psia
    Bo=[1.25, 1.24, 1.23],        # rb/STB
    Rs=[500, 480, 460],            # SCF/STB
    unit_system=UnitSystem.FIELD   # ← Specify unit system
)

reservoir = OilReservoir(
    pvt_properties=pvt,
    initial_pressure=3000,         # psia
    reservoir_temperature=180,     # °F
    unit_system=UnitSystem.FIELD   # ← Specify unit system
)

# All calculations happen in metric units internally
# Results are in metric units (can convert for display)
```

## Conversion Factors Used

| Property | Field Unit | Metric Unit | Conversion Factor |
|----------|-----------|-------------|-------------------|
| Pressure | psia | kgf/cm² | 1 psia = 0.0703069 kgf/cm² |
| Oil Volume | STB | m³ std | 1 STB = 0.158987 m³ |
| Gas Volume | SCF | m³ std | 1 SCF = 0.0283168 m³ |
| Temperature | °F | K | K = (°F - 32) × 5/9 + 273.15 |
| Oil FVF | rb/STB | m³/m³ std | Same numerical value |
| Gas FVF | rb/SCF | m³/m³ std | Complex conversion |
| GOR | SCF/STB | m³/m³ std | 1 SCF/STB = 0.178107 m³/m³ |
| Compressibility | 1/psi | 1/(kgf/cm²) | Multiply by 14.2233 |

## Testing

All unit conversions have been tested and verified:
```bash
python test_units.py
```

✓ Pressure conversion: ±0.1 psia accuracy
✓ Volume conversion: ±10 STB/SCF accuracy
✓ Temperature conversion: ±0.01 °F accuracy
✓ GOR conversion: ±0.1 SCF/STB accuracy
✓ All other conversions verified

## Backward Compatibility

✓ **Fully backward compatible** - existing code continues to work
- Default unit system is `METRIC` (same as before)
- If `unit_system` parameter is omitted, assumes metric units
- No breaking changes to existing API

## Files Modified

1. `material_balance/units.py` - NEW (380 lines)
2. `material_balance/pvt_properties.py` - Updated
3. `material_balance/oil_reservoir.py` - Updated
4. `material_balance/gas_reservoir.py` - Updated
5. `material_balance/__init__.py` - Updated
6. `UNIT_SYSTEM_GUIDE.md` - NEW
7. `test_units.py` - NEW
8. `examples/example_field_units.py` - NEW

## Benefits

1. **Flexibility**: Work with familiar units (metric or field)
2. **Automatic**: No manual conversion needed
3. **Accurate**: Uses standard petroleum industry conversion factors
4. **Consistent**: All calculations use same internal units
5. **Simple**: Just add `unit_system=UnitSystem.FIELD` parameter

## Future Enhancements

Possible improvements for future versions:
- Add output unit selection (currently results are always in metric)
- Support for SI units (Pa, m³)
- Support for other regional unit systems
- Add unit labels to plot axes
