"""
Utilities Module

Provides utility functions for the material balance framework.
"""

import numpy as np
from typing import Dict, Any, List


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
