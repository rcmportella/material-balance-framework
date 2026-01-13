"""
Gas Reservoir Material Balance Module

This module implements the material balance equation for gas reservoirs
to calculate initial gas in place (GIIP) based on production and pressure data.
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from .pvt_properties import PVTProperties
from .units import UnitSystem, UnitConverter


@dataclass
class GasProductionData:
    """Container for gas production data at different time points"""
    time: np.ndarray          # Time (days or other consistent unit)
    Gp: np.ndarray           # Cumulative gas production
    Wp: np.ndarray           # Cumulative water production
    pressure: np.ndarray     # Average reservoir pressure
    unit_system: UnitSystem = UnitSystem.METRIC  # Unit system for input data
    
    def __post_init__(self):
        """Convert lists to numpy arrays and convert to metric units if needed"""
        converter = UnitConverter()
        
        self.time = np.array(self.time)
        
        # Convert gas volume
        self.Gp = np.array(self.Gp)
        self.Gp = converter.gas_volume_to_metric(self.Gp, self.unit_system)
        
        # Convert water volume
        self.Wp = np.array(self.Wp)
        self.Wp = converter.oil_volume_to_metric(self.Wp, self.unit_system)
        
        # Convert pressure
        self.pressure = np.array(self.pressure)
        self.pressure = converter.pressure_to_metric(self.pressure, self.unit_system)
        
        # After conversion, all internal data is in metric units
        self.unit_system = UnitSystem.METRIC


class GasReservoir:
    """
    Gas Reservoir Material Balance Calculator
    
    Implements the material balance equation for gas reservoirs:
    
    For dry gas reservoir:
    G = Gp / (Bg/Bgi - 1)
    
    For gas reservoir with water influx:
    G = (Gp*Bg - We + Wp*Bw) / (Bg - Bgi)
    
    For P/Z plot method:
    P/Z = (Pi/Zi) * (1 - Gp/G)
    
    Where:
        G = Initial gas in place (GIIP) (m3 std)
        Gp = Cumulative gas produced (m3 std)
        Wp = Cumulative water produced (m3 std)
        Bg = Gas formation volume factor (m3/m3 std)
        Bw = Water formation volume factor (m3/m3 std)
        We = Cumulative water influx (m3)
        Z = Gas compressibility factor
        P = Pressure (kgf/cm2)
    """
    
    def __init__(self, 
                 pvt_properties: PVTProperties,
                 initial_pressure: float,
                 reservoir_temperature: float,
                 aquifer_influx: bool = False,
                 unit_system: UnitSystem = UnitSystem.METRIC):
        """
        Initialize Gas Reservoir Material Balance Calculator.
        
        Args:
            pvt_properties: PVT properties object with gas properties
            initial_pressure: Initial reservoir pressure
            reservoir_temperature: Reservoir temperature
            aquifer_influx: Whether to consider aquifer influx
            unit_system: Unit system for input/output (METRIC or FIELD)
        """
        self.pvt = pvt_properties
        self.unit_system = unit_system
        self.converter = UnitConverter()
        
        # Convert inputs to internal metric units
        self.Pi = self.converter.pressure_to_metric(initial_pressure, unit_system)
        self.T = self.converter.temperature_to_kelvin(reservoir_temperature, unit_system)
        self.aquifer_influx = aquifer_influx
        
        # Get initial properties (already in metric from PVT)
        self.initial_props = pvt_properties.get_properties_at_pressure(self.Pi)
        self.Bgi = self.initial_props.get('Bg')
        self.Zi = self.initial_props.get('z')
        
        if self.Bgi is None:
            raise ValueError("Gas formation volume factor (Bg) must be provided in PVT properties")
        if self.Zi is None:
            raise ValueError("Gas compressibility factor (z) must be provided in PVT properties")
    
    def calculate_GIIP(self, 
                      Gp: float, 
                      pressure: float,
                      Wp: float = 0.0,
                      We: float = 0.0) -> float:
        """
        Calculate Gas Initially In Place (GIIP).
        
        Args:
            Gp: Cumulative gas produced (m3 std)
            pressure: Current average reservoir pressure (kgf/cm2)
            Wp: Cumulative water produced (m3 std), default 0
            We: Cumulative water influx from aquifer (m3), default 0
            
        Returns:
            G: Initial gas in place (m3 std)
        """
        # Get properties at current pressure
        props = self.pvt.get_properties_at_pressure(pressure)
        Bg = props['Bg']
        Bw = props.get('Bw', 1.0)
        
        # Calculate GIIP based on whether aquifer is present
        if self.aquifer_influx or We > 0 or Wp > 0:
            # With water influx
            numerator = Gp * Bg - We + Wp * Bw
            denominator = Bg - self.Bgi
        else:
            # Dry gas reservoir (no water influx)
            numerator = Gp
            denominator = (Bg / self.Bgi) - 1
        
        if abs(denominator) < 1e-10:
            raise ValueError(f"Denominator in GIIP calculation is too small ({denominator}). " +
                           "Check if pressure has changed from initial pressure.")
        
        G = numerator / denominator
        
        return G
    
    def calculate_GIIP_pz_method(self, 
                                Gp: float, 
                                pressure: float,
                                z: Optional[float] = None) -> float:
        """
        Calculate GIIP using P/Z plot method.
        
        This method uses the linear relationship between P/Z and Gp.
        
        Args:
            Gp: Cumulative gas produced (m3 std)
            pressure: Current average reservoir pressure (kgf/cm2)
            z: Gas compressibility factor at current pressure (optional, will interpolate if not provided)
            
        Returns:
            G: Initial gas in place (m3 std)
        """
        if z is None:
            props = self.pvt.get_properties_at_pressure(pressure)
            z = props['z']
        
        # From P/Z = (Pi/Zi) * (1 - Gp/G)
        # Solving for G:
        pz = pressure / z
        pzi = self.Pi / self.Zi
        
        if abs(pzi - pz) < 1e-10:
            raise ValueError("P/Z has not changed from initial conditions. Need more pressure decline.")
        
        G = Gp / (1 - pz / pzi)
        
        return G
    
    def calculate_GIIP_from_production_data(self, 
                                           production_data: GasProductionData,
                                           We_values: Optional[np.ndarray] = None,
                                           method: str = 'standard') -> Tuple[np.ndarray, dict]:
        """
        Calculate GIIP from multiple production data points.
        
        Args:
            production_data: GasProductionData object with time series
            We_values: Water influx values for each time point (optional)
            method: Calculation method - 'standard' or 'pz' (P/Z method)
            
        Returns:
            Tuple of (G_values, statistics_dict)
            G_values: Array of calculated GIIP for each data point
            statistics: Dictionary with mean, std, etc.
        """
        n_points = len(production_data.time)
        G_values = np.zeros(n_points)
        
        if We_values is None:
            We_values = np.zeros(n_points)
        
        for i in range(n_points):
            try:
                if method == 'pz':
                    G_values[i] = self.calculate_GIIP_pz_method(
                        Gp=production_data.Gp[i],
                        pressure=production_data.pressure[i]
                    )
                else:  # standard method
                    G_values[i] = self.calculate_GIIP(
                        Gp=production_data.Gp[i],
                        pressure=production_data.pressure[i],
                        Wp=production_data.Wp[i],
                        We=We_values[i]
                    )
            except Exception as e:
                print(f"Warning: Could not calculate GIIP at point {i}: {e}")
                G_values[i] = np.nan
        
        # Calculate statistics (excluding NaN values)
        valid_G = G_values[~np.isnan(G_values)]
        
        if len(valid_G) == 0:
            raise ValueError("No valid GIIP calculations were possible")
        
        statistics = {
            'mean': np.mean(valid_G),
            'median': np.median(valid_G),
            'std': np.std(valid_G),
            'min': np.min(valid_G),
            'max': np.max(valid_G),
            'count': len(valid_G),
            'coefficient_of_variation': np.std(valid_G) / np.mean(valid_G) if np.mean(valid_G) != 0 else np.inf
        }
        
        return G_values, statistics
    
    def plot_pz_vs_gp(self, production_data: GasProductionData):
        """
        Create P/Z vs Gp plot.
        
        This is the classic gas reservoir material balance plot.
        A straight line should result, with the x-intercept being the GIIP.
        
        Args:
            production_data: GasProductionData object
            
        Returns:
            Figure and axes objects for the plot
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")
        
        n_points = len(production_data.time)
        pz_values = np.zeros(n_points)
        
        for i in range(n_points):
            props = self.pvt.get_properties_at_pressure(production_data.pressure[i])
            z = props['z']
            pz_values[i] = production_data.pressure[i] / z
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(production_data.Gp, pz_values, s=50, alpha=0.6, label='Data')
        
        # Fit line
        if len(production_data.Gp) > 1:
            coeffs = np.polyfit(production_data.Gp, pz_values, 1)
            
            # X-intercept is GIIP
            if coeffs[0] != 0:
                G_from_plot = -coeffs[1] / coeffs[0]
            else:
                G_from_plot = np.nan
            
            # Plot fitted line
            Gp_line = np.linspace(0, max(production_data.Gp) * 1.2, 100)
            pz_line = coeffs[0] * Gp_line + coeffs[1]
            ax.plot(Gp_line, pz_line, 'r--', label=f'G = {G_from_plot/1e6:.2f} Mm3')
            
            # Mark initial P/Z
            ax.axhline(y=self.Pi/self.Zi, color='g', linestyle=':', alpha=0.5, label=f'Pi/Zi = {self.Pi/self.Zi:.0f}')
        
        ax.set_xlabel('Cumulative Gas Production, Gp (m3 std)', fontsize=12)
        ax.set_ylabel('P/Z (kgf/cm2)', fontsize=12)
        ax.set_title('P/Z vs Gp Material Balance Plot', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis for large numbers
        ax.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
        
        return fig, ax
    
    def plot_pressure_history(self, production_data: GasProductionData):
        """
        Plot pressure and P/Z vs cumulative production.
        
        Args:
            production_data: GasProductionData object
            
        Returns:
            Figure and axes objects
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")
        
        # Calculate P/Z
        pz_values = np.zeros(len(production_data.time))
        for i in range(len(production_data.time)):
            props = self.pvt.get_properties_at_pressure(production_data.pressure[i])
            z = props['z']
            pz_values[i] = production_data.pressure[i] / z
        
        # Create subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Plot 1: Pressure vs Gp
        ax1.plot(production_data.Gp, production_data.pressure, 'b-o', markersize=5)
        ax1.set_xlabel('Cumulative Gas Production, Gp (m3 std)', fontsize=11)
        ax1.set_ylabel('Pressure (kgf/cm2)', fontsize=11)
        ax1.set_title('Pressure Decline', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
        
        # Plot 2: P/Z vs Gp
        ax2.plot(production_data.Gp, pz_values, 'r-o', markersize=5)
        ax2.set_xlabel('Cumulative Gas Production, Gp (m3 std)', fontsize=11)
        ax2.set_ylabel('P/Z (kgf/cm2)', fontsize=11)
        ax2.set_title('P/Z Decline', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
        
        plt.tight_layout()
        return fig, (ax1, ax2)
