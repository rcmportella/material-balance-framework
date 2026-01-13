"""
Utilities Module

Provides utility functions for the material balance framework.
"""

import numpy as np
import csv
from typing import Dict, Any, List, Optional


def format_number(value: float, unit: str = "") -> str:
    """
    Format large numbers with proper units and separators.
    
    Args:
        value: Number to format
        unit: Unit string (e.g., "m3", "m3 std")
        
    Returns:
        Formatted string
    """
    if abs(value) >= 1e9:
        return f"{value/1e9:,.2f} G{unit}"
    elif abs(value) >= 1e6:
        return f"{value/1e6:,.2f} M{unit}"
    elif abs(value) >= 1e3:
        return f"{value/1e3:,.2f} K{unit}"
    else:
        return f"{value:,.2f} {unit}"


def calculate_recovery_factor(N_or_G: float, Np_or_Gp: float) -> float:
    """
    Calculate recovery factor.
    
    Args:
        N_or_G: Initial oil (m3 std) or gas (m3 std) in place
        Np_or_Gp: Cumulative produced oil (m3 std) or gas (m3 std)
        
    Returns:
        Recovery factor (fraction)
    """
    if N_or_G <= 0:
        return 0.0
    return Np_or_Gp / N_or_G


def print_results_summary(results: Dict[str, Any], reservoir_type: str = "oil"):
    """
    Print a formatted summary of material balance results.
    
    Args:
        results: Dictionary containing calculation results
        reservoir_type: "oil" or "gas"
    """
    print("\n" + "="*60)
    print(f"MATERIAL BALANCE RESULTS - {reservoir_type.upper()} RESERVOIR")
    print("="*60)
    
    if reservoir_type.lower() == "oil":
        if 'mean' in results:
            print(f"\nInitial Oil In Place (STOIIP):")
            print(f"  Mean:     {format_number(results['mean'], 'm3 std')}")
            print(f"  Median:   {format_number(results['median'], 'm3 std')}")
            print(f"  Std Dev:  {format_number(results['std'], 'm3 std')}")
            print(f"  Range:    {format_number(results['min'], 'm3 std')} - {format_number(results['max'], 'm3 std')}")
            print(f"  CV:       {results['coefficient_of_variation']:.2%}")
        else:
            print(f"\nInitial Oil In Place (STOIIP): {format_number(results['N'], 'm3 std')}")
        
        if 'recovery_factor' in results:
            print(f"\nCurrent Recovery Factor: {results['recovery_factor']:.2%}")
    
    elif reservoir_type.lower() == "gas":
        if 'mean' in results:
            print(f"\nInitial Gas In Place (GIIP):")
            print(f"  Mean:     {format_number(results['mean'], 'm3 std')}")
            print(f"  Median:   {format_number(results['median'], 'm3 std')}")
            print(f"  Std Dev:  {format_number(results['std'], 'm3 std')}")
            print(f"  Range:    {format_number(results['min'], 'm3 std')} - {format_number(results['max'], 'm3 std')}")
            print(f"  CV:       {results['coefficient_of_variation']:.2%}")
        else:
            print(f"\nInitial Gas In Place (GIIP): {format_number(results['G'], 'm3 std')}")
        
        if 'recovery_factor' in results:
            print(f"\nCurrent Recovery Factor: {results['recovery_factor']:.2%}")
    
    print("\n" + "="*60 + "\n")


def validate_production_data(time: np.ndarray, 
                            production: np.ndarray, 
                            pressure: np.ndarray) -> bool:
    """
    Validate production data for consistency.
    
    Args:
        time: Time array
        production: Cumulative production array
        pressure: Pressure array
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # Check arrays have same length
    if not (len(time) == len(production) == len(pressure)):
        raise ValueError("Time, production, and pressure arrays must have the same length")
    
    # Check for negative values
    if np.any(time < 0):
        raise ValueError("Time values cannot be negative")
    
    if np.any(production < 0):
        raise ValueError("Production values cannot be negative")
    
    if np.any(pressure < 0):
        raise ValueError("Pressure values cannot be negative")
    
    # Check that time is monotonically increasing
    if not np.all(np.diff(time) >= 0):
        raise ValueError("Time array must be monotonically increasing")
    
    # Check that cumulative production is monotonically increasing
    if not np.all(np.diff(production) >= 0):
        raise ValueError("Cumulative production must be monotonically increasing")
    
    return True


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert between common petroleum engineering units.
    
    Args:
        value: Value to convert
        from_unit: Source unit
        to_unit: Target unit
        
    Returns:
        Converted value
    """
    # Pressure conversions
    pressure_conversions = {
        ('psi', 'kPa'): 6.89476,
        ('kPa', 'psi'): 0.145038,
        ('psi', 'bar'): 0.0689476,
        ('bar', 'psi'): 14.5038,
        ('bar', 'kPa'): 100.0,
        ('kPa', 'bar'): 0.01,
    }
    
    # Volume conversions
    volume_conversions = {
        ('bbl', 'm3'): 0.158987,
        ('m3', 'bbl'): 6.28981,
        ('ft3', 'm3'): 0.0283168,
        ('m3', 'ft3'): 35.3147,
        ('scf', 'm3'): 0.0283168,
        ('m3', 'scf'): 35.3147,
    }
    
    # Temperature conversions
    if from_unit == 'F' and to_unit == 'C':
        return (value - 32) * 5/9
    elif from_unit == 'C' and to_unit == 'F':
        return value * 9/5 + 32
    elif from_unit == 'F' and to_unit == 'R':
        return value + 459.67
    elif from_unit == 'C' and to_unit == 'K':
        return value + 273.15
    
    # Check pressure conversions
    key = (from_unit.lower(), to_unit.lower())
    if key in pressure_conversions:
        return value * pressure_conversions[key]
    
    # Check volume conversions
    if key in volume_conversions:
        return value * volume_conversions[key]
    
    raise ValueError(f"Conversion from {from_unit} to {to_unit} not supported")


def estimate_aquifer_influx_simple(We_constant: float, 
                                  pressure_drop: float, 
                                  time: float) -> float:
    """
    Simple aquifer influx estimation (for demonstration).
    
    For more accurate calculations, use specialized aquifer models
    (van Everdingen-Hurst, Carter-Tracy, Fetkovich).
    
    Args:
        We_constant: Aquifer constant (m3/(kgf/cm2))
        pressure_drop: Pressure drop from initial (kgf/cm2)
        time: Time (days)
        
    Returns:
        Cumulative water influx (m3)
    """
    # Very simplified model
    We = We_constant * pressure_drop * np.sqrt(time)
    return We


class MaterialBalanceReport:
    """
    Class to generate comprehensive reports from material balance calculations.
    """
    
    def __init__(self, reservoir_type: str):
        self.reservoir_type = reservoir_type
        self.results = {}
        
    def add_results(self, key: str, value: Any):
        """Add results to the report."""
        self.results[key] = value
    
    def generate_text_report(self) -> str:
        """Generate a text report."""
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append(f"MATERIAL BALANCE ANALYSIS REPORT - {self.reservoir_type.upper()} RESERVOIR")
        report_lines.append("=" * 70)
        report_lines.append("")
        
        for key, value in self.results.items():
            if isinstance(value, dict):
                report_lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    report_lines.append(f"  {sub_key}: {sub_value}")
            else:
                report_lines.append(f"{key}: {value}")
        
        report_lines.append("")
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)
    
    def save_report(self, filename: str):
        """Save report to file."""
        with open(filename, 'w') as f:
            f.write(self.generate_text_report())


def save_results_to_csv(results: Dict[str, Any], filename: str, 
                       reservoir_obj: Optional[Any] = None,
                       print_to_console: bool = True):
    """
    Save material balance results to a CSV file.
    
    Args:
        results: Dictionary containing calculation results (from calculate_STOIIP_from_production_data)
        filename: Output CSV filename
        reservoir_obj: Optional reservoir object (OilReservoir or GasReservoir) to get expansion terms
        print_to_console: If True, also print results to console (default: True)
    
    Example:
        N_values, stats = oil_res.calculate_STOIIP_from_production_data(prod_data)
        save_results_to_csv(stats, 'results.csv', oil_res)
    """
    # Prepare data
    data = []
    
    # Main results
    if 'mean' in results:
        data.append(['Parameter', 'Value', 'Unit'])
        data.append(['Mean STOIIP/GIIP', f"{results['mean']:.2f}", 'm³ std'])
        data.append(['Median STOIIP/GIIP', f"{results['median']:.2f}", 'm³ std'])
        data.append(['Std Dev', f"{results['std']:.2f}", 'm³ std'])
        data.append(['Min', f"{results['min']:.2f}", 'm³ std'])
        data.append(['Max', f"{results['max']:.2f}", 'm³ std'])
        data.append(['Coefficient of Variation', f"{results['coefficient_of_variation']:.4f}", ''])
        data.append(['Count', f"{results['count']}", 'points'])
    
    # Add expansion terms for ALL points if reservoir object is provided
    if reservoir_obj is not None and hasattr(reservoir_obj, 'Eo_values'):
        data.append(['', '', ''])  # Empty row
        data.append(['EXPANSION TERMS FOR ALL PRESSURE POINTS', '', ''])
        data.append(['Point', 'Pressure (kgf/cm²)', 'Eo', 'Eg', 'Efw', 'Et', 'F (m³)'])
        
        for i in range(len(reservoir_obj.pressure_values)):
            eo = reservoir_obj.Eo_values[i]
            eg = reservoir_obj.Eg_values[i]
            efw = reservoir_obj.Efw_values[i]
            et = reservoir_obj.Et_values[i]
            f_val = reservoir_obj.F_values[i]
            p_val = reservoir_obj.pressure_values[i]
            
            data.append([
                str(i + 1),
                f"{p_val:.2f}" if not np.isnan(p_val) else "N/A",
                f"{eo:.6f}" if not np.isnan(eo) else "N/A",
                f"{eg:.6f}" if not np.isnan(eg) else "N/A",
                f"{efw:.6f}" if not np.isnan(efw) else "N/A",
                f"{et:.6f}" if not np.isnan(et) else "N/A",
                f"{f_val:.2f}" if not np.isnan(f_val) else "N/A"
            ])
    
    # Save to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    
    # Print to console if requested
    if print_to_console:
        print(f"\n✓ Results saved to: {filename}")
        print("\nSummary:")
        for i, row in enumerate(data):
            if i < 10 and len(row) == 3 and row[0] and row[0] != 'Parameter':
                print(f"  {row[0]}: {row[1]} {row[2]}")
        
        if reservoir_obj is not None and hasattr(reservoir_obj, 'Eo_values'):
            print(f"\n  Expansion terms included for {len(reservoir_obj.pressure_values)} pressure points")
            print(f"  {row[0]}: {row[1]} {row[2]}")
    
    return filename


def save_production_analysis_to_csv(production_data, N_values: np.ndarray, 
                                   filename: str, reservoir_obj: Optional[Any] = None,
                                   print_to_console: bool = True):
    """
    Save detailed production analysis to CSV with STOIIP/GIIP and expansion terms at each point.
    
    Args:
        production_data: ProductionData or GasProductionData object
        N_values: Array of calculated STOIIP/GIIP values for each time point
        filename: Output CSV filename
        reservoir_obj: Optional reservoir object to include expansion terms
        print_to_console: If True, also print summary to console (default: True)
    
    Example:
        N_values, stats = oil_res.calculate_STOIIP_from_production_data(prod_data)
        save_production_analysis_to_csv(prod_data, N_values, 'production_analysis.csv', oil_res)
    """
    # Build header
    header = ['Time (days)', 'Pressure (kgf/cm²)', 'Cumulative Production (m³)', 'STOIIP/GIIP (m³ std)']
    
    # Add expansion term columns if reservoir object is provided
    if reservoir_obj is not None and hasattr(reservoir_obj, 'Eo_values'):
        header.extend(['Eo', 'Eg', 'Efw', 'Et', 'F (m³)'])
    
    data = [header]
    
    for i in range(len(production_data.time)):
        # Get cumulative production (Np for oil, Gp for gas)
        if hasattr(production_data, 'Np'):
            cum_prod = production_data.Np[i]
        else:
            cum_prod = production_data.Gp[i]
        
        row = [
            f"{production_data.time[i]:.0f}",
            f"{production_data.pressure[i]:.2f}",
            f"{cum_prod:.2f}",
            f"{N_values[i]:.2f}" if not np.isnan(N_values[i]) else "N/A"
        ]
        
        # Add expansion terms if available
        if reservoir_obj is not None and hasattr(reservoir_obj, 'Eo_values'):
            if i < len(reservoir_obj.Eo_values):
                eo = reservoir_obj.Eo_values[i]
                eg = reservoir_obj.Eg_values[i]
                efw = reservoir_obj.Efw_values[i]
                et = reservoir_obj.Et_values[i]
                f_val = reservoir_obj.F_values[i]
                
                row.extend([
                    f"{eo:.6f}" if not np.isnan(eo) else "N/A",
                    f"{eg:.6f}" if not np.isnan(eg) else "N/A",
                    f"{efw:.6f}" if not np.isnan(efw) else "N/A",
                    f"{et:.6f}" if not np.isnan(et) else "N/A",
                    f"{f_val:.2f}" if not np.isnan(f_val) else "N/A"
                ])
        
        data.append(row)
    
    # Save to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    
    # Print to console if requested
    if print_to_console:
        print(f"\n✓ Production analysis saved to: {filename}")
        print(f"  Total data points: {len(production_data.time)}")
        valid_points = np.sum(~np.isnan(N_values))
        print(f"  Valid calculations: {valid_points}")
        if reservoir_obj is not None and hasattr(reservoir_obj, 'Eo_values'):
            print(f"  Expansion terms included: Eo, Eg, Efw, Et, F")
    
    return filename

