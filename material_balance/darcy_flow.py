"""
Darcy Flow Module for Radial Flow in Porous Media

This module implements Darcy's Law for radial flow in oil reservoirs,
allowing calculation of oil flow rates and pressure drawdowns.

Radial Flow Equation:
    q = C * k * h * (Pe - Pwf) / (mu * Bo * (ln(re/rw) + S))

Where:
    - q: Oil flow rate
    - k: Permeability
    - h: Reservoir thickness
    - Pe: Outer boundary pressure
    - Pwf: Bottomhole flowing pressure
    - mu: Oil viscosity
    - Bo: Oil formation volume factor
    - re: Outer boundary radius (drainage radius)
    - rw: Well radius
    - S: Skin factor (damage or stimulation)
    - C: Unit conversion constant
"""

import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
from .units import UnitSystem


@dataclass
class DarcyFlowParameters:
    """
    Container for Darcy flow calculation parameters.
    
    Units depend on unit_system:
    
    FIELD Units:
        - k: permeability (mD)
        - h: thickness (ft)
        - Pe: outer boundary pressure (psia)
        - Pwf: bottomhole pressure (psia)
        - mu: oil viscosity (cp)
        - Bo: oil formation volume factor (dimensionless)
        - re: outer boundary radius (ft)
        - rw: well radius (ft)
        - S: skin factor (dimensionless)
        - q: flow rate (STB/day)
    
    METRIC Units:
        - k: permeability (mD)
        - h: thickness (m)
        - Pe: outer boundary pressure (kgf/cm²)
        - Pwf: bottomhole pressure (kgf/cm²)
        - mu: oil viscosity (cp)
        - Bo: oil formation volume factor (dimensionless)
        - re: outer boundary radius (m)
        - rw: well radius (m)
        - S: skin factor (dimensionless)
        - q: flow rate (m³/day)
    """
    k: float  # Permeability (mD)
    h: float  # Thickness
    mu: float  # Oil viscosity (cp)
    Bo: float  # Oil formation volume factor
    re: float  # Outer boundary radius
    rw: float  # Well radius
    S: float = 0.0  # Skin factor (default: 0, no damage)
    
    # One of these must be None (to be calculated)
    q: Optional[float] = None  # Flow rate
    Pe: Optional[float] = None  # Outer boundary pressure
    Pwf: Optional[float] = None  # Bottomhole pressure
    
    unit_system: UnitSystem = UnitSystem.METRIC
    
    def __post_init__(self):
        """Validate input parameters"""
        # Check that either (Pe and Pwf) or q is provided, but not both
        pressure_given = (self.Pe is not None and self.Pwf is not None)
        flow_given = (self.q is not None)
        
        if pressure_given and flow_given:
            raise ValueError(
                "Cannot specify both pressure difference (Pe, Pwf) and flow rate (q). "
                "One must be None to be calculated."
            )
        
        if not pressure_given and not flow_given:
            raise ValueError(
                "Must specify either pressure difference (Pe and Pwf) or flow rate (q)."
            )
        
        # Validate positive values
        if self.k <= 0:
            raise ValueError(f"Permeability must be positive, got {self.k}")
        if self.h <= 0:
            raise ValueError(f"Thickness must be positive, got {self.h}")
        if self.mu <= 0:
            raise ValueError(f"Viscosity must be positive, got {self.mu}")
        if self.Bo <= 0:
            raise ValueError(f"Formation volume factor must be positive, got {self.Bo}")
        if self.re <= 0:
            raise ValueError(f"Outer radius must be positive, got {self.re}")
        if self.rw <= 0:
            raise ValueError(f"Well radius must be positive, got {self.rw}")
        if self.re <= self.rw:
            raise ValueError(f"Outer radius ({self.re}) must be greater than well radius ({self.rw})")
        
        # Validate pressures if given
        if pressure_given:
            if self.Pe <= 0:
                raise ValueError(f"Outer boundary pressure must be positive, got {self.Pe}")
            if self.Pwf <= 0:
                raise ValueError(f"Bottomhole pressure must be positive, got {self.Pwf}")
            if self.Pe <= self.Pwf:
                raise ValueError(
                    f"Outer boundary pressure ({self.Pe}) must be greater than "
                    f"bottomhole pressure ({self.Pwf})"
                )
        
        # Validate flow rate if given
        if flow_given and self.q <= 0:
            raise ValueError(f"Flow rate must be positive, got {self.q}")


class DarcyRadialFlow:
    """
    Calculator for radial flow using Darcy's Law.
    
    Supports both field units (STB/day, psia, ft) and metric units (m³/day, kgf/cm², m).
    Can calculate either:
        1. Flow rate (q) given pressures (Pe and Pwf)
        2. Pressure drawdown (Pe - Pwf) given flow rate (q)
    """
    
    # Unit conversion constants
    # Field units: q[STB/day] = 0.007082153 * k[mD] * h[ft] * dP[psi] / (mu[cp] * Bo * (ln(re/rw) + S))
    CONSTANT_FIELD = 0.007082153
    
    # Metric units: q[m³/day] = 0.543439 * k[mD] * h[m] * dP[kgf/cm²] / (mu[cp] * Bo * (ln(re/rw) + S))
    CONSTANT_METRIC = 0.543439
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.METRIC):
        """
        Initialize Darcy flow calculator.
        
        Args:
            unit_system: Unit system for calculations (METRIC or FIELD)
        """
        self.unit_system = unit_system
        self.constant = self.CONSTANT_METRIC if unit_system == UnitSystem.METRIC else self.CONSTANT_FIELD
    
    def calculate_flow_rate(self, params: DarcyFlowParameters) -> Dict[str, Any]:
        """
        Calculate oil flow rate from given pressures.
        
        Args:
            params: DarcyFlowParameters with Pe and Pwf specified
            
        Returns:
            Dictionary with results including:
                - q: Flow rate
                - dP: Pressure drawdown (Pe - Pwf)
                - skin_effect: Pressure drop due to skin
                - productivity_index: Well productivity index
        """
        if params.Pe is None or params.Pwf is None:
            raise ValueError("Both Pe and Pwf must be specified to calculate flow rate")
        
        # Pressure drawdown
        dP = params.Pe - params.Pwf
        
        # Geometric term
        ln_term = np.log(params.re / params.rw) + params.S
        
        # Calculate flow rate using Darcy's equation
        q = (self.constant * params.k * params.h * dP) / (params.mu * params.Bo * ln_term)
        
        # Productivity Index (PI = q / dP)
        PI = q / dP if dP > 0 else 0
        
        # Skin effect (additional pressure drop due to skin)
        # dP_skin = (q * mu * Bo * S) / (0.007082 * k * h)  for field units
        dP_skin = (q * params.mu * params.Bo * params.S) / (self.constant * params.k * params.h)
        
        # Dimensionless skin effect
        dP_ideal = (q * params.mu * params.Bo * np.log(params.re / params.rw)) / (self.constant * params.k * params.h)
        
        results = {
            'q': q,
            'dP': dP,
            'Pe': params.Pe,
            'Pwf': params.Pwf,
            'productivity_index': PI,
            'skin_effect_pressure': dP_skin,
            'ideal_dP': dP_ideal,
            'ln_term': ln_term,
            'unit_system': params.unit_system
        }
        
        return results
    
    def calculate_pressure_drawdown(self, params: DarcyFlowParameters) -> Dict[str, Any]:
        """
        Calculate pressure drawdown from given flow rate.
        
        If Pe is given, calculates Pwf.
        If Pwf is given, calculates Pe.
        If neither is given, returns only dP.
        
        Args:
            params: DarcyFlowParameters with q specified
            
        Returns:
            Dictionary with results including:
                - dP: Pressure drawdown (Pe - Pwf)
                - Pe or Pwf: Calculated pressure (if one was provided)
                - productivity_index: Well productivity index
        """
        if params.q is None:
            raise ValueError("Flow rate (q) must be specified to calculate pressure drawdown")
        
        # Geometric term
        ln_term = np.log(params.re / params.rw) + params.S
        
        # Calculate pressure drawdown from Darcy's equation
        dP = (params.q * params.mu * params.Bo * ln_term) / (self.constant * params.k * params.h)
        
        # Determine Pe or Pwf
        Pe = params.Pe
        Pwf = params.Pwf
        
        if Pe is not None and Pwf is None:
            # Calculate Pwf
            Pwf = Pe - dP
            if Pwf < 0:
                raise ValueError(
                    f"Calculated bottomhole pressure is negative ({Pwf:.2f}). "
                    f"Flow rate may be too high for given conditions."
                )
        elif Pwf is not None and Pe is None:
            # Calculate Pe
            Pe = Pwf + dP
        
        # Productivity Index
        PI = params.q / dP if dP > 0 else 0
        
        # Skin effect
        dP_skin = (params.q * params.mu * params.Bo * params.S) / (self.constant * params.k * params.h)
        dP_ideal = (params.q * params.mu * params.Bo * np.log(params.re / params.rw)) / (self.constant * params.k * params.h)
        
        results = {
            'dP': dP,
            'Pe': Pe,
            'Pwf': Pwf,
            'q': params.q,
            'productivity_index': PI,
            'skin_effect_pressure': dP_skin,
            'ideal_dP': dP_ideal,
            'ln_term': ln_term,
            'unit_system': params.unit_system
        }
        
        return results
    
    def calculate(self, params: DarcyFlowParameters) -> Dict[str, Any]:
        """
        Main calculation method that automatically determines what to calculate.
        
        Args:
            params: DarcyFlowParameters object
            
        Returns:
            Dictionary with calculation results
        """
        if params.q is None:
            # Calculate flow rate
            return self.calculate_flow_rate(params)
        else:
            # Calculate pressure drawdown
            return self.calculate_pressure_drawdown(params)
    
    def print_results(self, results: Dict[str, Any]):
        """
        Print formatted results.
        
        Args:
            results: Dictionary returned by calculate() method
        """
        unit_system = results.get('unit_system', self.unit_system)
        
        print("\n" + "="*70)
        print("DARCY RADIAL FLOW CALCULATION RESULTS")
        print("="*70)
        
        if unit_system == UnitSystem.FIELD:
            print("\nUnit System: FIELD UNITS")
            print(f"  Flow Rate (q):              {results['q']:,.2f} STB/day")
            print(f"  Pressure Drawdown (dP):     {results['dP']:,.2f} psi")
            if results['Pe'] is not None:
                print(f"  Outer Boundary Pressure:    {results['Pe']:,.2f} psia")
            if results['Pwf'] is not None:
                print(f"  Bottomhole Pressure:        {results['Pwf']:,.2f} psia")
            print(f"  Productivity Index (PI):    {results['productivity_index']:,.4f} STB/day/psi")
            print(f"  Skin Effect Pressure Drop:  {results['skin_effect_pressure']:,.2f} psi")
            print(f"  Ideal Pressure Drop (S=0):  {results['ideal_dP']:,.2f} psi")
        else:
            print("\nUnit System: METRIC UNITS")
            print(f"  Flow Rate (q):              {results['q']:,.2f} m³/day")
            print(f"  Pressure Drawdown (dP):     {results['dP']:,.2f} kgf/cm²")
            if results['Pe'] is not None:
                print(f"  Outer Boundary Pressure:    {results['Pe']:,.2f} kgf/cm²")
            if results['Pwf'] is not None:
                print(f"  Bottomhole Pressure:        {results['Pwf']:,.2f} kgf/cm²")
            print(f"  Productivity Index (PI):    {results['productivity_index']:,.4f} m³/day/(kgf/cm²)")
            print(f"  Skin Effect Pressure Drop:  {results['skin_effect_pressure']:,.2f} kgf/cm²")
            print(f"  Ideal Pressure Drop (S=0):  {results['ideal_dP']:,.2f} kgf/cm²")
        
        print(f"\n  Geometric Term (ln(re/rw)+S): {results['ln_term']:.4f}")
        
        print("="*70)
    
    def sensitivity_analysis(self, 
                           base_params: DarcyFlowParameters,
                           parameter_name: str,
                           values: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Perform sensitivity analysis on a parameter.
        
        Args:
            base_params: Base case parameters
            parameter_name: Name of parameter to vary ('k', 'S', 'Pe', etc.)
            values: Array of values to test
            
        Returns:
            Dictionary with arrays of results for each value
        """
        results_q = []
        results_dP = []
        results_PI = []
        
        for value in values:
            # Create new params with modified value
            params_dict = {
                'k': base_params.k,
                'h': base_params.h,
                'mu': base_params.mu,
                'Bo': base_params.Bo,
                're': base_params.re,
                'rw': base_params.rw,
                'S': base_params.S,
                'q': base_params.q,
                'Pe': base_params.Pe,
                'Pwf': base_params.Pwf,
                'unit_system': base_params.unit_system
            }
            params_dict[parameter_name] = value
            
            try:
                test_params = DarcyFlowParameters(**params_dict)
                result = self.calculate(test_params)
                
                results_q.append(result['q'])
                results_dP.append(result['dP'])
                results_PI.append(result['productivity_index'])
            except Exception as e:
                print(f"Warning: Failed for {parameter_name}={value}: {e}")
                results_q.append(np.nan)
                results_dP.append(np.nan)
                results_PI.append(np.nan)
        
        return {
            parameter_name: values,
            'q': np.array(results_q),
            'dP': np.array(results_dP),
            'PI': np.array(results_PI)
        }


def calculate_drainage_radius(area: float, unit_system: UnitSystem = UnitSystem.METRIC) -> float:
    """
    Calculate drainage radius from drainage area.
    
    Args:
        area: Drainage area (acres for FIELD, m² for METRIC)
        unit_system: Unit system
        
    Returns:
        Drainage radius (ft for FIELD, m for METRIC)
    """
    if unit_system == UnitSystem.FIELD:
        # Convert acres to ft²: 1 acre = 43560 ft²
        area_ft2 = area * 43560
        re = np.sqrt(area_ft2 / np.pi)
    else:
        # Area already in m²
        re = np.sqrt(area / np.pi)
    
    return re


def calculate_skin_factor(k: float, h: float, q: float, dP_actual: float, dP_ideal: float,
                         mu: float, Bo: float, re: float, rw: float,
                         unit_system: UnitSystem = UnitSystem.METRIC) -> float:
    """
    Calculate skin factor from measured pressure data.
    
    Args:
        k: Permeability (mD)
        h: Thickness
        q: Flow rate
        dP_actual: Actual measured pressure drawdown
        dP_ideal: Ideal pressure drawdown (from theory or test)
        mu: Viscosity (cp)
        Bo: Formation volume factor
        re: Outer radius
        rw: Well radius
        unit_system: Unit system
        
    Returns:
        Skin factor (dimensionless)
    """
    # S = (dP_actual - dP_ideal) * (constant * k * h) / (q * mu * Bo)
    constant = DarcyRadialFlow.CONSTANT_METRIC if unit_system == UnitSystem.METRIC else DarcyRadialFlow.CONSTANT_FIELD
    
    S = ((dP_actual - dP_ideal) * constant * k * h) / (q * mu * Bo)
    
    return S
