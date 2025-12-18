"""
Oil Reservoir Material Balance Module

This module implements the general material balance equation for oil reservoirs
to calculate initial oil in place (STOIIP) based on production and pressure data.
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from .pvt_properties import PVTProperties


@dataclass
class ProductionData:
    """Container for production data at different time points"""
    time: np.ndarray  # Time (days or other consistent unit)
    Np: np.ndarray    # Cumulative oil production (m3 std)
    Gp: np.ndarray    # Cumulative gas production (m3 std)
    Wp: np.ndarray    # Cumulative water production (m3 std)
    pressure: np.ndarray  # Average reservoir pressure (kgf/cm2)
    
    def __post_init__(self):
        """Convert lists to numpy arrays"""
        self.time = np.array(self.time)
        self.Np = np.array(self.Np)
        self.Gp = np.array(self.Gp)
        self.Wp = np.array(self.Wp)
        self.pressure = np.array(self.pressure)


class OilReservoir:
    """
    Oil Reservoir Material Balance Calculator
    
    Implements the general material balance equation:
    N = (Np*Bo + (Gp - Np*Rs)*Bg + Wp*Bw) / (Eo + m*Eg + Efw)
    
    Where:
        N = Initial oil in place (m3 std)
        Np = Cumulative oil produced (m3 std)
        Gp = Cumulative gas produced (m3 std)
        Wp = Cumulative water produced (m3 std)
        Bo, Bg, Bw = Formation volume factors (m3/m3 std)
        Rs = Solution gas-oil ratio (m3/m3 std)
        m = Ratio of initial gas cap volume to initial oil volume
        Eo = Oil expansion term
        Eg = Gas cap expansion term
        Efw = Water and formation expansion term
    """
    
    def __init__(self, 
                 pvt_properties: PVTProperties,
                 initial_pressure: float,
                 reservoir_temperature: float,
                 m: float = 0.0,
                 aquifer_influx: bool = False):
        """
        Initialize Oil Reservoir Material Balance Calculator.
        
        Args:
            pvt_properties: PVT properties object
            initial_pressure: Initial reservoir pressure (kgf/cm2)
            reservoir_temperature: Reservoir temperature (°C)
            m: Gas cap size ratio (G/N*Boi), default 0 for undersaturated
            aquifer_influx: Whether to consider aquifer influx
        """
        self.pvt = pvt_properties
        self.Pi = initial_pressure
        self.T = reservoir_temperature
        self.m = m
        self.aquifer_influx = aquifer_influx
        
        # Get initial properties
        self.initial_props = pvt_properties.get_properties_at_pressure(initial_pressure)
        self.Boi = self.initial_props['Bo']
        self.Rsi = self.initial_props['Rs']
        self.Bgi = self.initial_props.get('Bg', None)
        
    def calculate_expansion_terms(self, pressure: float) -> Tuple[float, float, float]:
        """
        Calculate expansion terms for material balance equation.
        
        Args:
            pressure: Current reservoir pressure (kgf/cm2)
            
        Returns:
            Tuple of (Eo, Eg, Efw) expansion terms
        """
        # Get properties at current pressure
        props = self.pvt.get_properties_at_pressure(pressure)
        Bo = props['Bo']
        Rs = props['Rs']
        Bg = props.get('Bg', 0)
        Bw = props.get('Bw', 1.0)
        
        # Oil expansion term
        Eo = (Bo - self.Boi) + (self.Rsi - Rs) * Bg
        
        # Gas cap expansion term
        if self.m > 0 and self.Bgi is not None:
            Eg = self.Boi * ((Bg / self.Bgi) - 1)
        else:
            Eg = 0.0
        
        # Water and formation expansion term
        cw = props.get('cw', 43e-6)  # Default water compressibility (1/(kgf/cm2))
        cf = props.get('cf', 43e-6)  # Default formation compressibility (1/(kgf/cm2))
        Swi = 0.2  # Initial water saturation (can be made a parameter)
        
        delta_P = self.Pi - pressure
        Efw = (1 + self.m) * self.Boi * (cw * Swi + cf) * delta_P
        
        return Eo, Eg, Efw
    
    def calculate_STOIIP(self, 
                        Np: float, 
                        Gp: float, 
                        Wp: float, 
                        pressure: float,
                        We: float = 0.0) -> float:
        """
        Calculate Stock Tank Oil Initially In Place (STOIIP).
        
        Args:
            Np: Cumulative oil produced (m3 std)
            Gp: Cumulative gas produced (m3 std)
            Wp: Cumulative water produced (m3 std)
            pressure: Current average reservoir pressure (kgf/cm2)
            We: Cumulative water influx from aquifer (m3), default 0
            
        Returns:
            N: Initial oil in place (m3 std)
        """
        # Get properties at current pressure
        props = self.pvt.get_properties_at_pressure(pressure)
        Bo = props['Bo']
        Rs = props['Rs']
        Bg = props.get('Bg', 0)
        Bw = props.get('Bw', 1.0)
        
        # Calculate expansion terms
        Eo, Eg, Efw = self.calculate_expansion_terms(pressure)
        
        # Underground withdrawal
        F = Np * Bo + (Gp - Np * Rs) * Bg + Wp * Bw - We
        
        # Total expansion
        Et = Eo + self.m * Eg + Efw
        
        if Et <= 0:
            raise ValueError(f"Total expansion is non-positive ({Et}). Check pressure data and PVT properties.")
        
        # Calculate STOIIP
        N = F / Et
        
        return N
    
    def calculate_STOIIP_from_production_data(self, 
                                             production_data: ProductionData,
                                             We_values: Optional[np.ndarray] = None) -> Tuple[np.ndarray, dict]:
        """
        Calculate STOIIP from multiple production data points.
        
        This method calculates STOIIP for each data point and can be used
        for material balance plots and averaging.
        
        Args:
            production_data: ProductionData object with time series
            We_values: Water influx values for each time point (optional)
            
        Returns:
            Tuple of (N_values, statistics_dict)
            N_values: Array of calculated STOIIP for each data point
            statistics: Dictionary with mean, std, etc.
        """
        n_points = len(production_data.time)
        N_values = np.zeros(n_points)
        
        if We_values is None:
            We_values = np.zeros(n_points)
        
        for i in range(n_points):
            try:
                N_values[i] = self.calculate_STOIIP(
                    Np=production_data.Np[i],
                    Gp=production_data.Gp[i],
                    Wp=production_data.Wp[i],
                    pressure=production_data.pressure[i],
                    We=We_values[i]
                )
            except Exception as e:
                print(f"Warning: Could not calculate STOIIP at point {i}: {e}")
                N_values[i] = np.nan
        
        # Calculate statistics (excluding NaN values)
        valid_N = N_values[~np.isnan(N_values)]
        
        if len(valid_N) == 0:
            raise ValueError("No valid STOIIP calculations were possible")
        
        statistics = {
            'mean': np.mean(valid_N),
            'median': np.median(valid_N),
            'std': np.std(valid_N),
            'min': np.min(valid_N),
            'max': np.max(valid_N),
            'count': len(valid_N),
            'coefficient_of_variation': np.std(valid_N) / np.mean(valid_N) if np.mean(valid_N) != 0 else np.inf
        }
        
        return N_values, statistics
    
    def plot_material_balance(self, 
                            production_data: ProductionData,
                            We_values: Optional[np.ndarray] = None):
        """
        Create material balance plots (F vs Et).
        
        This creates the classic material balance straight-line plot where
        the slope represents the initial oil in place.
        
        Args:
            production_data: ProductionData object
            We_values: Water influx values (optional)
            
        Returns:
            Figure and axes objects for the plot
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")
        
        n_points = len(production_data.time)
        F_values = np.zeros(n_points)
        Et_values = np.zeros(n_points)
        
        if We_values is None:
            We_values = np.zeros(n_points)
        
        for i in range(n_points):
            props = self.pvt.get_properties_at_pressure(production_data.pressure[i])
            Bo = props['Bo']
            Rs = props['Rs']
            Bg = props.get('Bg', 0)
            Bw = props.get('Bw', 1.0)
            
            # Underground withdrawal
            F_values[i] = (production_data.Np[i] * Bo + 
                          (production_data.Gp[i] - production_data.Np[i] * Rs) * Bg + 
                          production_data.Wp[i] * Bw - We_values[i])
            
            # Total expansion
            Eo, Eg, Efw = self.calculate_expansion_terms(production_data.pressure[i])
            Et_values[i] = Eo + self.m * Eg + Efw
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(Et_values, F_values, s=50, alpha=0.6)
        
        # Fit line and calculate N from slope
        if len(Et_values) > 1:
            coeffs = np.polyfit(Et_values, F_values, 1)
            N_from_slope = coeffs[0]
            
            # Plot fitted line
            Et_line = np.linspace(0, max(Et_values) * 1.1, 100)
            F_line = coeffs[0] * Et_line + coeffs[1]
            ax.plot(Et_line, F_line, 'r--', label=f'N = {N_from_slope:,.0f} STB')
        
        ax.set_xlabel('Total Expansion, Et (m3/m3 std)', fontsize=12)
        ax.set_ylabel('Underground Withdrawal, F (m3)', fontsize=12)
        ax.set_title('Material Balance Plot (F vs Et)', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig, ax
