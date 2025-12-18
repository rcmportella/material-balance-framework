# Metric Units System

The Material Balance Framework has been updated to work with **metric units** instead of field units.

## Unit System

### Pressure
- **Unit**: kgf/cm² (kilogram-force per square centimeter)
- **Conversion**: 1 psia = 0.0703069 kgf/cm² | 1 kgf/cm² = 14.2233 psia

### Volume
- **Oil/Water**: m³ std (cubic meters at standard conditions)
- **Gas**: m³ std (cubic meters at standard conditions)
- **Reservoir volumes**: m³ (cubic meters)

### Temperature
- **Input**: °C (Celsius) for correlations
- **Calculations**: K (Kelvin) for gas calculations (K = °C + 273.15)

### Formation Volume Factors
- **Bo**: m³/m³ std (reservoir m³ per standard m³)
- **Bg**: m³/m³ std (reservoir m³ per standard m³)
- **Bw**: m³/m³ std (reservoir m³ per standard m³)

### Gas-Oil Ratio
- **Rs**: m³/m³ std (standard gas m³ per standard oil m³)

### Compressibility
- **co, cw, cf, cg**: 1/(kgf/cm²)

## Conversion Factors

### From Field Units to Metric Units

```python
# Pressure
kgf_cm2 = psia * 0.0703069

# Volume
m3_std_oil = STB * 0.158987
m3_std_gas = SCF * 0.0283168
m3_reservoir = rb * 0.158987

# Temperature
celsius = (fahrenheit - 32) * 5/9
kelvin = celsius + 273.15

# Gas-Oil Ratio
m3_m3 = scf_stb / 178.107

# Compressibility
comp_metric = comp_psi * 14.2233
```

## Example Data Conversions

### Oil Reservoir Example

**Field Units:**
- Pressure: 3000 psia → **210 kgf/cm²**
- Oil Production: 4,700,000 STB → **747,300 m³ std**
- Gas Production: 2,350 MMSCF → **66,552,000 m³ std**
- Temperature: 180°F → **82°C**

**Rs Conversion:**
- 500 SCF/STB → **2.81 m³/m³ std**

### Gas Reservoir Example

**Field Units:**
- Pressure: 4000 psia → **281 kgf/cm²**
- Gas Production: 62 BSCF → **1,755 Mm³ std**
- Temperature: 660°R (200°F) → **366.5 K (93.3°C)**

## PVT Correlations

All correlations (Standing, Vasquez-Beggs, Hall-Yarborough) have been adapted to:
1. Accept metric inputs
2. Convert internally to field units for correlation calculations
3. Convert results back to metric units

### Example: Standing Rs Correlation

```python
Rs = standing_Rs(
    P=140,        # kgf/cm²
    gamma_g=0.65, # dimensionless
    gamma_o=0.85, # dimensionless
    T=82          # °C
)
# Returns Rs in m³/m³ std
```

## Gas Formation Volume Factor (Bg)

The formula for Bg in metric units:

```
Bg = 0.00351 * z * T / P
```

Where:
- Bg: m³/m³ std
- z: dimensionless
- T: K (Kelvin)
- P: kgf/cm²

Compare to field units: `Bg = 0.02827 * z * T / P` (rb/SCF, °R, psia)

## Default Compressibility Values

Updated default values for metric units:
- Water: **43×10⁻⁶ (kgf/cm²)⁻¹** (equivalent to 3×10⁻⁶ psi⁻¹)
- Formation: **57×10⁻⁶ (kgf/cm²)⁻¹** (equivalent to 4×10⁻⁶ psi⁻¹)

## Output Formatting

Results are displayed with metric-appropriate prefixes:
- **K**: thousand (10³)
- **M**: million (10⁶)
- **G**: billion/giga (10⁹)

Example output:
```
Initial Oil In Place (STOIIP):
  Mean:     274.97 Mm³ std
  Median:   130.71 Mm³ std
```

## Material Balance Equations

The fundamental equations remain the same, only the units change:

### Oil Reservoir
```
N = F / Et

where:
F = Np·Bo + (Gp - Np·Rs)·Bg + Wp·Bw - We    [m³]
Et = Eo + m·Eg + Efw                         [m³/m³ std]

Result: N in m³ std
```

### Gas Reservoir
```
G = Gp / ((Bg/Bgi) - 1)

Result: G in m³ std
```

## Notes

1. **Standard Conditions**: Metric standard conditions assumed as 15°C (288.15 K) and 1.0332 kgf/cm²
2. **Consistency**: All inputs must be in the same unit system (metric)
3. **Correlations**: Internally convert to field units for established correlations, then convert back
4. **Plotting**: Axis labels updated to reflect metric units

## References

- API gravity and specific gravity relationships remain unchanged (dimensionless)
- Gas specific gravity relative to air (dimensionless)
- Oil specific gravity relative to water (dimensionless)
