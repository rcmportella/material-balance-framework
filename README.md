# Material Balance Framework for Reservoir Engineering

A comprehensive Python framework for calculating initial volumes in-place (STOIIP/GIIP) using material balance equations for oil and gas reservoirs based on production data and pressure measurements.

## Features

### Oil Reservoirs
- **General Material Balance Equation** implementation
- Support for gas cap drive (m-factor)
- **Gas cap size determination** - Automated methods to determine unknown gas cap size
- Water influx modeling capability
- Multiple PVT property handling (Bo, Rs, Bg, Bw)
- Material balance plotting (F vs Et)
- Statistical analysis of STOIIP estimates

### Gas Reservoirs
- **Standard material balance** for dry gas
- **P/Z method** for gas in place calculation
- Water influx considerations
- Gas compressibility factor (Z-factor) handling
- P/Z vs Gp plotting
- Pressure decline analysis

### PVT Properties
- Flexible PVT data input with interpolation
- Built-in correlations:
  - Standing correlation (Bo, Rs)
  - Vasquez-Beggs correlation (Bo)
  - Hall-Yarborough correlation (Z-factor)
  - Lee-Gonzalez-Eakin correlation (gas viscosity)
  - Beggs-Robinson correlation (oil viscosity)
  - Formation volume factor calculations
- Support for measured PVT data
- **PVT Table Generator GUI** ([material_balance/PVT_table.py](material_balance/PVT_table.py)) with plotting, Excel export and OPM/Eclipse (`PVDG`/`PVTO`) export

### Darcy Radial Flow
- **Oil flow rate calculations** using Darcy's Law
- Pressure drawdown analysis
- Support for both field and metric units
- Skin factor effects (damage/stimulation)
- Productivity index calculations
- Sensitivity analysis tools

### Utilities
- Production data validation
- Unit conversions
- Formatted output and reporting
- Statistical analysis
- Recovery factor calculations

## Installation

### Requirements
```
Python >= 3.7
numpy >= 1.19.0
matplotlib >= 3.3.0 (optional, for plotting)
```

### Install Dependencies
```bash
pip install numpy matplotlib
```

## Project Structure

```
PetroleumEngineering/
├── material_balance/
│   ├── __init__.py              # Package initialization
│   ├── oil_reservoir.py         # Oil reservoir material balance
│   ├── gas_reservoir.py         # Gas reservoir material balance
│   ├── pvt_properties.py        # PVT properties and correlations
│   ├── PVT_table.py             # PVT table generator GUI (Excel/OPM export)
│   └── utils.py                 # Utility functions
├── examples/
│   └── example_usage.py         # Example scripts
└── README.md                    # This file
```

## Quick Start

### Example 1: Oil Reservoir

```python
from material_balance import OilReservoir, PVTProperties
from material_balance.oil_reservoir import ProductionData

# Define PVT properties
pvt = PVTProperties(
    pressure=[3000, 2800, 2600, 2400, 2200],
    Bo=[1.25, 1.24, 1.23, 1.22, 1.21],        # rb/STB
    Rs=[500, 480, 460, 440, 420],              # SCF/STB
    Bg=[0.0008, 0.00085, 0.0009, 0.00095, 0.001],  # rb/SCF
    Bw=[1.02, 1.02, 1.02, 1.02, 1.02],        # rb/STB
    cw=[3e-6, 3e-6, 3e-6, 3e-6, 3e-6],        # 1/psi
    cf=[4e-6, 4e-6, 4e-6, 4e-6, 4e-6]         # 1/psi
)

# Initialize reservoir
oil_res = OilReservoir(
    pvt_properties=pvt,
    initial_pressure=3000,  # psia
    reservoir_temperature=180,  # °F
    m=0.2  # Gas cap ratio
)

# Production data
prod_data = ProductionData(
    time=[0, 365, 730, 1095, 1460],
    Np=[0, 500000, 1200000, 2000000, 2900000],  # STB
    Gp=[0, 250e6, 600e6, 1000e6, 1450e6],       # SCF
    Wp=[0, 10000, 25000, 42000, 61000],         # STB
    pressure=[3000, 2800, 2600, 2400, 2200]     # psia
)

# Calculate STOIIP
N_values, statistics = oil_res.calculate_STOIIP_from_production_data(prod_data)

print(f"Mean STOIIP: {statistics['mean']:,.0f} STB")
print(f"Standard Deviation: {statistics['std']:,.0f} STB")
print(f"Coefficient of Variation: {statistics['coefficient_of_variation']:.2%}")

# Create material balance plot
fig, ax = oil_res.plot_material_balance(prod_data)
```

### Example 2: Gas Reservoir

```python
from material_balance import GasReservoir, PVTProperties
from material_balance.gas_reservoir import GasProductionData

# Define PVT properties
pressure_data = [4000, 3800, 3600, 3400, 3200]
z_data = [0.85, 0.84, 0.83, 0.82, 0.81]
T = 660  # Rankine (200°F + 460)

# Calculate Bg
Bg_data = [0.02827 * z * T / P for z, P in zip(z_data, pressure_data)]

pvt = PVTProperties(
    pressure=pressure_data,
    Bg=Bg_data,
    z=z_data
)

# Initialize gas reservoir
gas_res = GasReservoir(
    pvt_properties=pvt,
    initial_pressure=4000,
    reservoir_temperature=T
)

# Gas production data
gas_prod_data = GasProductionData(
    time=[0, 365, 730, 1095, 1460],
    Gp=[0, 5e9, 12e9, 20e9, 29e9],  # SCF
    Wp=[0, 0, 0, 0, 0],              # STB
    pressure=[4000, 3800, 3600, 3400, 3200]  # psia
)

# Calculate GIIP using standard method
G_values, statistics = gas_res.calculate_GIIP_from_production_data(
    gas_prod_data, 
    method='standard'
)

print(f"Mean GIIP: {statistics['mean']/1e9:.2f} BSCF")

# Calculate using P/Z method
G_values_pz, stats_pz = gas_res.calculate_GIIP_from_production_data(
    gas_prod_data,
    method='pz'
)

# Create P/Z plot
fig, ax = gas_res.plot_pz_vs_gp(gas_prod_data)
```

### Example 3: Using PVT Correlations

```python
from material_balance.pvt_properties import CorrelationsPVT

# Standing correlation for Rs
Rs = CorrelationsPVT.standing_Rs(
    P=2500,        # psia
    gamma_g=0.65,  # Gas specific gravity
    gamma_o=0.85,  # Oil specific gravity
    T=180          # °F
)

# Standing correlation for Bo
Bo = CorrelationsPVT.standing_Bo(
    Rs=450,        # SCF/STB
    gamma_g=0.65,
    gamma_o=0.85,
    T=180
)

# Hall-Yarborough Z-factor
z = CorrelationsPVT.gas_z_factor_hall_yarborough(
    P=3000,        # psia
    T=660,         # Rankine
    gamma_g=0.65
)

# Gas formation volume factor
Bg = CorrelationsPVT.gas_Bg(P=3000, T=660, z=z)

print(f"Rs = {Rs:.1f} SCF/STB")
print(f"Bo = {Bo:.4f} rb/STB")
print(f"Z = {z:.4f}")
print(f"Bg = {Bg:.6f} rb/SCF")
```

### Example 4: Darcy Radial Flow

```python
from material_balance import DarcyRadialFlow, DarcyFlowParameters, UnitSystem

# Calculate flow rate from known pressures (Metric)
params = DarcyFlowParameters(
    k=100,          # Permeability: 100 mD
    h=10,           # Thickness: 10 m
    Pe=200,         # Reservoir pressure: 200 kgf/cm²
    Pwf=150,        # Wellbore pressure: 150 kgf/cm²
    mu=2.0,         # Viscosity: 2 cp
    Bo=1.25,        # Formation volume factor: 1.25
    re=300,         # Drainage radius: 300 m
    rw=0.1,         # Well radius: 0.1 m
    S=0,            # No skin
    unit_system=UnitSystem.METRIC
)

calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
results = calculator.calculate(params)
calculator.print_results(results)

print(f"Flow rate: {results['q']:.2f} m³/day")
print(f"Productivity Index: {results['productivity_index']:.4f} m³/day/(kgf/cm²)")

# Calculate bottomhole pressure from desired rate (Field)
params_field = DarcyFlowParameters(
    k=50,           # Permeability: 50 mD
    h=30,           # Thickness: 30 ft
    Pe=3000,        # Reservoir pressure: 3000 psia
    q=500,          # Desired rate: 500 STB/day
    mu=1.5,         # Viscosity: 1.5 cp
    Bo=1.2,         # Formation volume factor: 1.2
    re=745,         # Drainage radius: 745 ft
    rw=0.3,         # Well radius: 0.3 ft
    S=0,            # No skin
    unit_system=UnitSystem.FIELD
)

calculator_field = DarcyRadialFlow(unit_system=UnitSystem.FIELD)
results_field = calculator_field.calculate(params_field)

print(f"Required Pwf: {results_field['Pwf']:.1f} psia")
print(f"Drawdown: {results_field['dP']:.1f} psi")
```

## Well Extrapolation App (Excel + GUI)

The script `examples/extrapola_producao_pocos.py` provides decline-curve extrapolation
from Excel workbooks and interactive plotting/export.

### Input columns supported

The parser accepts at least the following columns (with flexible header aliases):

- Poço
- Categoria
- Classe
- Fluido
- Operação
- Zona
- Início Produção
- Qg (M m3/dia)
- Qo (m3/dia)
- Qw (m3/dia)
- Di (including unit-suffixed headers such as `Di (1/ano)`)
- b

Notes:

- For gas rows, `qi = Qg`.
- For oil rows, `qi = Qo`.
- The workbook is explicitly closed immediately after reading to avoid file locks.

### Decline model

- Hyperbolic decline: `q = qi / (1 + b * Di * t)^(1/b)`
- Exponential fallback when `b = 0`: `q = qi * exp(-Di * t)`

The extrapolation end date is hard-coded to `31/12/2052`.

### Shut-in threshold behavior

- Gas threshold: user-configurable in the GUI (default `0.0`)
- Oil threshold: user-configurable in the GUI (default `0.0`)

If `qi` is at or below threshold, the interval starts shut-in (`q = 0`).
During extrapolation, if `q <= threshold`, production is shut-in from that point.
Threshold changes can be applied from the GUI and trigger a full extrapolation refresh.

### Duplicate rows for the same well

When the same well appears in multiple rows, the app supports two extrapolation modes:

1. `Sequencial (encerra produção anterior)`:
    - uses priority order (`P1+PDP`, `P1+PDNP`, `P1+PUD`, `P2`, `P3`),
    - resolves overlaps using highest rate (then priority on ties),
    - truncates the previous interval at the next start date.
2. `Independente (soma às produções anteriores)`:
    - keeps prior intervals active,
    - sums active contributions for the same well over time,
    - integrates cumulative production with trapezoidal integration for smoother declines.

The extrapolation mode can be changed directly in the GUI.

### Exports

The output workbook includes:

- `vazao_pocos`
- `acumulada_pocos`
- `vazao_conc_fluido`
- `vazao_conc_categoria`
- `vazao_conc_classe`
- `acum_conc_fluido`
- `acum_conc_categoria`
- `acum_conc_classe`

`acum_conc_categoria` is exported in wide format:

- Data
- Fluido
- Acumulada P1
- Acumulada P2
- Acumulada P3

`vazao_conc_categoria` is exported in wide format with the corresponding
instantaneous flow columns `Vazão P1`, `Vazão P2`, and `Vazão P3`.

`vazao_conc_classe` is exported in wide format with the corresponding
instantaneous flow columns `Vazão PDP`, `Vazão PDNP`, `Vazão PUD`, `Vazão 5PRB`,
and `Vazão 6POS`.

The sum `P1 + P2 + P3` is numerically consistent with the fluid total cumulative
(subject only to floating-point tolerance).

`acum_conc_classe` is exported in wide format:

- Data
- Fluido
- Acumulada PDP
- Acumulada PDNP
- Acumulada PUD
- Acumulada 5PRB
- Acumulada 6POS

## Material Balance Equations

### Oil Reservoir

The general material balance equation for oil reservoirs:

```
N = F / Et

where:
F = Np·Bo + (Gp - Np·Rs)·Bg + Wp·Bw - We
Et = Eo + m·Eg + Efw

Eo = (Bo - Boi) + (Rsi - Rs)·Bg
Eg = Boi·((Bg/Bgi) - 1)
Efw = (1 + m)·Boi·(cw·Swi + cf)·ΔP
```

**Variables:**
- N = Initial oil in place (STB)
- Np = Cumulative oil produced (STB)
- Gp = Cumulative gas produced (SCF)
- Wp = Cumulative water produced (STB)
- We = Cumulative water influx (rb)
- Bo, Bg, Bw = Formation volume factors
- Rs = Solution gas-oil ratio (SCF/STB)
- m = Gas cap size ratio
- cw, cf = Water and formation compressibility

### Gas Reservoir

**Standard Method:**
```
G = Gp / ((Bg/Bgi) - 1)
```

**P/Z Method:**
```
P/Z = (Pi/Zi)·(1 - Gp/G)

Solving for G:
G = Gp / (1 - (P/Z)/(Pi/Zi))
```

**Variables:**
- G = Initial gas in place (SCF)
- Gp = Cumulative gas produced (SCF)
- Bg = Gas formation volume factor (rb/SCF)
- Z = Gas compressibility factor
- P = Pressure (psia)

## Running Examples

```bash
cd examples
python example_usage.py
```

This will run all three examples and display:
- STOIIP calculation results with statistics
- GIIP calculation results using both methods
- PVT correlations demonstration
- Material balance plots (if matplotlib is installed)

## Advanced Features

### Gas Cap Size Determination

For oil reservoirs with unknown gas cap size, the framework provides automated methods to determine the optimal gas cap parameter (m) by analyzing the linearity of F vs (Eo + m×Eg) plots:

```python
# Method 1: Visual analysis with multiple m values
m_values = np.arange(0.1, 1.0, 0.1)
fig, axes, r_squared = reservoir.plot_gas_cap_determination(
    production_data=production_data,
    m_values=m_values
)

# Method 2: Automatically find optimal m
optimal_m, results = reservoir.determine_optimal_m(
    production_data=production_data,
    show_plot=True
)

print(f"Optimal gas cap size: m = {optimal_m:.3f}")
print(f"R² = {results['optimal_r_squared']:.6f}")
```

See [Gas Cap Determination Guide](GAS_CAP_DETERMINATION_GUIDE.md) for detailed documentation.

### Water Influx Modeling

```python
# For oil reservoirs
We_values = np.array([0, 5000, 12000, 20000, 30000])  # rb
N_values, stats = oil_res.calculate_STOIIP_from_production_data(
    prod_data,
    We_values=We_values
)
```

### Single Point Calculation

```python
# Calculate STOIIP at a specific point
N = oil_res.calculate_STOIIP(
    Np=2000000,    # STB
    Gp=1000e6,     # SCF
    Wp=42000,      # STB
    pressure=2400, # psia
    We=20000       # rb
)
```

### Custom PVT Property Interpolation

```python
# Get properties at any pressure
props = pvt.get_properties_at_pressure(2750)
print(f"Bo at 2750 psia: {props['Bo']}")
print(f"Rs at 2750 psia: {props['Rs']}")
```

## Output and Reporting

The framework provides formatted output:

```
==============================================================
MATERIAL BALANCE RESULTS - OIL RESERVOIR
==============================================================

Initial Oil In Place (STOIIP):
  Mean:     45.30 MMSTB
  Median:   45.15 MMSTB
  Std Dev:  1.25 MMSTB
  Range:    43.80 MMSTB - 47.10 MMSTB
  CV:       2.76%

Current Recovery Factor: 6.40%

==============================================================
```

## Unit System

The framework primarily uses **Field Units**:
- Pressure: psia
- Volume (Oil): STB (Stock Tank Barrels)
- Volume (Gas): SCF (Standard Cubic Feet)
- Volume (Reservoir): rb (Reservoir Barrels)
- Temperature: °F (or °R for absolute temperature)
- Time: days

Unit conversion utilities are provided in `utils.py`.

## Validation and Quality Control

The framework includes:
- Input data validation
- Monotonicity checks on production data
- Range checks on calculated values
- Statistical analysis for quality assessment
- Coefficient of variation (CV) for uncertainty quantification

**Interpretation Guidelines:**
- CV < 5%: High confidence in results
- CV 5-10%: Moderate confidence
- CV > 10%: High uncertainty, review data quality

## Theory and Background

### Material Balance Method

The material balance method is a fundamental reservoir engineering technique that:
1. Applies conservation of mass to the reservoir system
2. Relates production volumes to pressure changes
3. Accounts for fluid expansion and compression
4. Provides estimates of initial volumes in place

### Key Assumptions

- Average reservoir pressure is representative
- PVT properties are accurate
- Production data is cumulative and accurate
- Reservoir is a tank (0-D model)
- No significant pressure gradients

### Applications

- Initial volume estimation (STOIIP/GIIP)
- Recovery factor prediction
- Drive mechanism identification
- Aquifer strength evaluation
- Field performance monitoring

## Troubleshooting

### Common Issues

1. **Large CV in results**: Check data quality, especially pressure measurements
2. **Negative STOIIP/GIIP**: Verify PVT data and ensure proper pressure ordering
3. **Import errors**: Ensure numpy is installed and paths are correct
4. **Plotting errors**: Install matplotlib: `pip install matplotlib`

## References

1. Craft, B.C. and Hawkins, M.F., "Applied Petroleum Reservoir Engineering"
2. Dake, L.P., "Fundamentals of Reservoir Engineering"
3. Tarek Ahmed, "Reservoir Engineering Handbook"
4. McCain, W.D., "The Properties of Petroleum Fluids"

## Contributing

Contributions are welcome! Areas for enhancement:
- Additional PVT correlations
- Aquifer models (van Everdingen-Hurst, Carter-Tracy)
- Water drive analysis
- Gas cap expansion models
- GUI interface
- Additional validation methods

## License

This framework is provided for educational and professional use in petroleum engineering applications.

## Author

Petroleum Engineering Team

## Version

1.0.0 - December 2025

## Today's Update (2026-07-17)

This repository was updated with a major improvement to the Excel-based well history and decline-fit workflow in [examples/plota_producao_pocos.py](examples/plota_producao_pocos.py):

- Added workbook selection at startup and interactive well switching in the GUI.
- Unified plotting in a single figure with dual y-axes and support for multiple fit overlays per well.
- Added interval-based decline fitting with `Auto` selection (Exponential, Harmonic, Hyperbolic) and forced model selection.
- Added the `Asymptotic Exponential` model (for Qw) with scaling metadata support (`scale_min`, `scale_max`, `normalized`).
- Implemented fit export/import to Excel (`decline_fits` sheet), including fit mode and interval metadata.
- Improved import compatibility with both label styles (`Qg/Qo/Qw`) and internal names (`Qgm/Qom/Qwm`), plus whitespace normalization.
- Fixed loaded-fit plotting issues by preserving aligned `fit_dates` and `fit_values` from reconstructed fits during import.
- Added a `Load Workbook` button in the GUI to replace the currently loaded dataset without restarting the app.

Sample fit and data workbooks were also included/updated in this commit to preserve reproducibility of the GUI flow.

---

For questions or support, please refer to the example scripts or consult petroleum engineering textbooks on material balance methods.

## New App: Well Production Extrapolation (2026-08-06)

The repository now includes a dedicated GUI app for Excel-based decline extrapolation:

- Script: [examples/extrapola_producao_pocos.py](examples/extrapola_producao_pocos.py)
- Input workbook example: `SMC_Reservas.xlsx`
- Main purpose: extrapolate well flow rates and cumulative production using exponential decline, with monthly time stepping.

### What It Does

- Reads well metadata and decline parameters from Excel (`Poço`, `Fluido`, `Zona`, `Início Produção`, `Qi`, `Di`).
- Plots `Vazão` or `Volume acumulado` in a Tkinter interface.
- Supports individual well selection or all wells by fluid (`Gás` / `Óleo`).
- Uses monthly advancement to the first day of each month during extrapolation.
- Stops extrapolation when production reaches threshold:
    - Gas: `2.0` (workbook units)
    - Oil: `1.0` (workbook units)

### Export to Excel

The app exports calculated results to a `.xlsx` file with the following sheets:

- `vazao_pocos`: per-well flow rate time series (includes `Zona`)
- `acumulada_pocos`: per-well cumulative series (single continuous cumulative curve per well/fluid)
- `vazao_conc_fluido`: concatenated flow rate by fluid for all wells
- `acum_conc_fluido`: concatenated cumulative by fluid for all wells

Export date format is `dd/mm/yyyy`.

### Physical Consistency Check

During data load/extrapolation, the app detects overlapping production intervals for the same well in different zones and emits warnings, since simultaneous production from multiple zones for the same well is physically inconsistent in this workflow.

### Run

```bash
python examples/extrapola_producao_pocos.py
```

Optional headless mode:

```bash
python examples/extrapola_producao_pocos.py --headless [workbook_path]
```

## New App: PVT Table Generator (2026-08-27)

A dedicated Tkinter GUI for generating pressure-dependent PVT tables and exporting them for use in Excel or reservoir simulators:

- Script: [material_balance/PVT_table.py](material_balance/PVT_table.py)
- Correlations used: Vasquez-Beggs/Standing (Bo, Rs), Hall-Yarborough (Z), Lee-Gonzalez-Eakin (gas viscosity), Beggs-Robinson (oil viscosity)

### What It Does

- Calculates `Bo`, `Bg`, `Rs`, `Z`, `co`, gas viscosity (`mu_g`) and oil viscosity (`mu_o`) across a pressure range at a fixed temperature, honoring the bubble point pressure.
- Plots all properties against pressure in a single window.
- Lets you pick a **METRIC** (bar, m³, °C) or **FIELD** (psia, bbl, scf, °F) unit system for inputs, plots and Excel export; viscosities are always in cP and API/gamma_g are unaffected (dimensionless).
- Closes the underlying matplotlib figure and forces the process to exit when the window is closed, so it doesn't linger in the terminal.

### Exports

- **Excel**: full property table plus an input-parameters sheet, using the selected unit system's units.
- **OPM/Eclipse keywords**: `PVDG` (gas pressure, Bg, gas viscosity) and `PVTO` (Rs, bubble point pressure, oil FVF, oil viscosity), written in the currently selected unit system (METRIC: bar and sm3/sm3; FIELD: psia, rb/Mscf and Mscf/stb). Pressures above the bubble point are appended as undersaturated continuation rows under the highest-Rs row, per the format's requirements.

### Run

```bash
python material_balance/PVT_table.py
```
