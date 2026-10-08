"""
Oil Reservoir Material Balance Module

This module implements the general material balance equation for oil reservoirs
to calculate initial oil in place (STOIIP) based on production and pressure data.
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from .pvt_properties import PVTProperties
from .units import UnitSystem, UnitConverter


@dataclass
class ProductionData:
    """Container for production data at different time points"""
    time: np.ndarray  # Time (days or other consistent unit)
    Np: np.ndarray    # Cumulative oil production
    Gp: np.ndarray    # Cumulative gas production
    Wp: np.ndarray    # Cumulative water production
    pressure: np.ndarray  # Average reservoir pressure
    unit_system: UnitSystem = UnitSystem.METRIC  # Unit system for input data
    Winj: Optional[np.ndarray] = None  # Cumulative injected water at surface conditions
    Ginj: Optional[np.ndarray] = None  # Cumulative injected gas at standard conditions
    We: Optional[np.ndarray] = None  # Cumulative aquifer influx at reservoir conditions
    
    def __post_init__(self):
        """Convert lists to numpy arrays and convert to metric units if needed"""
        converter = UnitConverter()
        
        self.time = np.array(self.time)
        
        # Convert volumes
        self.Np = np.array(self.Np)
        self.Np = np.atleast_1d(converter.oil_volume_to_metric(self.Np, self.unit_system))
        
        self.Gp = np.array(self.Gp)
        self.Gp = np.atleast_1d(converter.gas_volume_to_metric(self.Gp, self.unit_system))
        
        self.Wp = np.array(self.Wp)
        self.Wp = np.atleast_1d(converter.oil_volume_to_metric(self.Wp, self.unit_system))

        self.Winj = np.zeros_like(self.Wp) if self.Winj is None else np.array(self.Winj)
        self.Winj = np.atleast_1d(
            converter.oil_volume_to_metric(self.Winj, self.unit_system)
        )

        self.Ginj = np.zeros_like(self.Gp) if self.Ginj is None else np.array(self.Ginj)
        self.Ginj = np.atleast_1d(
            converter.gas_volume_to_metric(self.Ginj, self.unit_system)
        )

        self.We = np.zeros_like(self.Wp) if self.We is None else np.array(self.We)
        self.We = np.atleast_1d(
            converter.reservoir_volume_to_metric(self.We, self.unit_system)
        )
        
        # Convert pressure
        self.pressure = np.array(self.pressure)
        self.pressure = np.atleast_1d(
            converter.pressure_to_metric(self.pressure, self.unit_system)
        )
        
        # After conversion, all internal data is in metric units
        self.unit_system = UnitSystem.METRIC


class OilReservoir:
    """
    Oil Reservoir Material Balance Calculator
    
    Implements the general material balance equation:
    N = (Np*Bo + (Gp - Np*Rs)*Bg + Wp*Bw - Winj*Bw - Ginj*Bg - We)
        / (Eo + m*Eg + Efw)
    
    Where:
        N = Initial oil in place (m3 std)
        Np = Cumulative oil produced (m3 std)
        Gp = Cumulative gas produced (m3 std)
        Wp = Cumulative water produced (m3 std)
        Winj = Cumulative water injected (m3 std)
        Ginj = Cumulative gas injected (m3 std)
        We = Cumulative aquifer influx at reservoir conditions (m3)
        Bo, Bg, Bw = Formation volume factors (m3/m3 std)
        Rs = Solution gas-oil ratio (m3/m3 std)
        m = Ratio of initial gas cap volume to initial oil volume
        Eo = Oil expansion term
        Eg = Gas cap expansion term
        Efw = Water and formation expansion term
        Positive Winj, Ginj, and We reduce net underground withdrawal F
    """
    
    def __init__(self, 
                 pvt_properties: PVTProperties,
                 initial_pressure: float,
                 reservoir_temperature: float,
                 m: float = 0.0,
                 aquifer_influx: bool = False,
                 unit_system: UnitSystem = UnitSystem.METRIC,
                 cw: Optional[float] = None,
                 cf: Optional[float] = None,
                 swi: float = 0.2):
        """
        Initialize Oil Reservoir Material Balance Calculator.
        
        Args:
            pvt_properties: PVT properties object
            initial_pressure: Initial reservoir pressure
            reservoir_temperature: Reservoir temperature
            m: Gas cap size ratio (G/N*Boi), default 0 for undersaturated
            aquifer_influx: Whether to consider aquifer influx
            unit_system: Unit system for input/output (METRIC or FIELD)
            cw: Water compressibility in 1/(kgf/cm2); PVT/default value if omitted
            cf: Formation compressibility in 1/(kgf/cm2); PVT/default value if omitted
            swi: Initial water saturation, as a fraction
        """
        self.pvt = pvt_properties
        self.unit_system = unit_system
        self.converter = UnitConverter()
        
        # Convert inputs to internal metric units
        self.Pi = self.converter.pressure_to_metric(initial_pressure, unit_system)
        self.T = self.converter.temperature_to_kelvin(reservoir_temperature, unit_system)
        self.m = m
        self.aquifer_influx = aquifer_influx
        self.cw = cw
        self.cf = cf
        self.swi = swi
        
        # Get initial properties (already in metric from PVT)
        self.initial_props = pvt_properties.get_properties_at_pressure(self.Pi)
        self.Boi = self.initial_props['Bo']
        self.Rsi = self.initial_props['Rs']
        self.Bgi = self.initial_props.get('Bg', None)
        
        # Storage for expansion terms for all calculation points
        self.Eo_values = []
        self.Eg_values = []
        self.Efw_values = []
        self.Et_values = []
        self.F_values = []
        self.withdrawal_terms_values = {}
        self.pressure_values = []
        
        # Last calculated values (for backward compatibility)
        self.Eo = None
        self.Eg = None
        self.Efw = None
        self.Et = None
        self.F = None
        self.withdrawal_terms = {}
        self.last_pressure = None
        
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
        if self.Bgi is not None:
            Eg = self.Boi * ((Bg / self.Bgi) - 1)
        else:
            Eg = 0.0
        
        # Water and formation expansion term
        cw = self.cw if self.cw is not None else props.get('cw', 43e-6)
        cf = self.cf if self.cf is not None else props.get('cf', 14.223e-6)
        
        delta_P = self.Pi - pressure
        Efw = (1 + self.m) * self.Boi * (cw * self.swi + cf) * delta_P
        
        return Eo, Eg, Efw
    
    def _calculate_withdrawal_terms(
        self,
        Np: float,
        Gp: float,
        Wp: float,
        pressure: float,
        Winj: float = 0.0,
        Ginj: float = 0.0,
        We: float = 0.0,
    ) -> dict[str, float]:
        props = self.pvt.get_properties_at_pressure(pressure)
        Bo = props['Bo']
        Rs = props['Rs']
        Bg = props.get('Bg', 0)
        Bw = props.get('Bw', 1.0)

        terms = {
            'oil_production': Np * Bo,
            'free_gas_production': (Gp - Np * Rs) * Bg,
            'water_production': Wp * Bw,
            'water_injection': Winj * Bw,
            'gas_injection': Ginj * Bg,
            'water_influx': We,
        }
        terms['production_total'] = sum(
            terms[name] for name in ('oil_production', 'free_gas_production', 'water_production')
        )
        terms['F'] = (
            terms['production_total'] - terms['water_injection']
            - terms['gas_injection'] - terms['water_influx']
        )
        return terms

    def calculate_STOIIP(self, 
                        Np: float, 
                        Gp: float, 
                        Wp: float, 
                        pressure: float,
                        We: float = 0.0,
                        Winj: float = 0.0,
                        Ginj: float = 0.0) -> float:
        """
        Calculate Stock Tank Oil Initially In Place (STOIIP).
        
        Args:
            Np: Cumulative oil produced (m3 std)
            Gp: Cumulative gas produced (m3 std)
            Wp: Cumulative water produced (m3 std)
            Winj: Cumulative water injected (m3 std)
            Ginj: Cumulative gas injected (m3 std)
            pressure: Current average reservoir pressure (kgf/cm2)
            We: Cumulative aquifer influx at reservoir conditions (m3), default 0
            
        Returns:
            N: Initial oil in place (m3 std)
        """
        # Calculate expansion terms
        Eo, Eg, Efw = self.calculate_expansion_terms(pressure)
        
        self.withdrawal_terms = self._calculate_withdrawal_terms(
            Np, Gp, Wp, pressure, Winj=Winj, Ginj=Ginj, We=We
        )
        F = self.withdrawal_terms['F']
        
        # Total expansion
        Et = Eo + self.m * Eg + Efw
        
        # Store last calculated values (for single-point calculations)
        self.Eo = Eo
        self.Eg = Eg
        self.Efw = Efw
        self.Et = Et
        self.F = F
        self.last_pressure = pressure
        
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
        
        # Clear previous arrays
        self.Eo_values = []
        self.Eg_values = []
        self.Efw_values = []
        self.Et_values = []
        self.F_values = []
        term_names = (
            'oil_production', 'free_gas_production', 'water_production',
            'water_injection', 'gas_injection', 'water_influx', 'production_total',
        )
        self.withdrawal_terms_values = {name: [] for name in term_names}
        self.pressure_values = []
        
        if We_values is None:
            We_values = production_data.We
        
        for i in range(n_points):
            try:
                N_values[i] = self.calculate_STOIIP(
                    Np=production_data.Np[i],
                    Gp=production_data.Gp[i],
                    Wp=production_data.Wp[i],
                    pressure=production_data.pressure[i],
                    We=We_values[i],
                    Winj=production_data.Winj[i],
                    Ginj=production_data.Ginj[i],
                )
                # Store expansion terms for this point
                self.Eo_values.append(self.Eo)
                self.Eg_values.append(self.Eg)
                self.Efw_values.append(self.Efw)
                self.Et_values.append(self.Et)
                self.F_values.append(self.F)
                for name in term_names:
                    self.withdrawal_terms_values[name].append(self.withdrawal_terms[name])
                self.pressure_values.append(production_data.pressure[i])
            except Exception as e:
                print(f"Warning: Could not calculate STOIIP at point {i}: {e}")
                N_values[i] = np.nan
                # Store NaN for failed calculations
                self.Eo_values.append(np.nan)
                self.Eg_values.append(np.nan)
                self.Efw_values.append(np.nan)
                self.Et_values.append(np.nan)
                self.F_values.append(np.nan)
                for name in term_names:
                    self.withdrawal_terms_values[name].append(np.nan)
                self.pressure_values.append(production_data.pressure[i])
        
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
            We_values = production_data.We
        
        for i in range(n_points):
            F_values[i] = self._calculate_withdrawal_terms(
                production_data.Np[i], production_data.Gp[i], production_data.Wp[i],
                production_data.pressure[i], Winj=production_data.Winj[i],
                Ginj=production_data.Ginj[i], We=We_values[i],
            )['F']
            
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
    
    def plot_gas_cap_determination(self, 
                                   production_data: ProductionData,
                                   m_values: Optional[np.ndarray] = None,
                                   We_values: Optional[np.ndarray] = None) -> Tuple:
        """
        Create plots to determine gas cap size (m) by plotting F vs (Eo + m*Eg).
        
        This method creates subplots for different values of m. The correct value 
        of m should produce the straightest line through the data points.
        
        Args:
            production_data: ProductionData object with time series
            m_values: Array of m values to test (default: 0.1 to 0.9 in steps of 0.1)
            We_values: Water influx values for each time point (optional)
            
        Returns:
            Tuple of (fig, axes, r_squared_dict)
            fig: Figure object
            axes: Array of axes objects
            r_squared_dict: Dictionary with R² values for each m
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")
        
        if m_values is None:
            m_values = np.arange(0.1, 1.0, 0.1)
        
        n_points = len(production_data.time)
        
        if We_values is None:
            We_values = production_data.We
        
        # Calculate F values (independent of m)
        F_values = np.zeros(n_points)
        for i in range(n_points):
            F_values[i] = self._calculate_withdrawal_terms(
                production_data.Np[i], production_data.Gp[i], production_data.Wp[i],
                production_data.pressure[i], Winj=production_data.Winj[i],
                Ginj=production_data.Ginj[i], We=We_values[i],
            )['F']
        
        # Calculate Eo and Eg for each pressure point
        Eo_values = np.zeros(n_points)
        Eg_values = np.zeros(n_points)
        
        for i in range(n_points):
            Eo, Eg, _ = self.calculate_expansion_terms(production_data.pressure[i])
            Eo_values[i] = Eo
            Eg_values[i] = Eg
        
        # Create subplots
        n_plots = len(m_values)
        n_cols = 3
        n_rows = int(np.ceil(n_plots / n_cols))
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
        axes = axes.flatten() if n_plots > 1 else [axes]
        
        r_squared_dict = {}
        
        for idx, m in enumerate(m_values):
            ax = axes[idx]
            
            # Calculate E_total = Eo + m*Eg
            E_total = Eo_values + m * Eg_values
            
            # Plot data points
            ax.scatter(E_total, F_values, s=50, alpha=0.6, color='blue')
            
            # Fit line
            if len(E_total) > 1:
                coeffs = np.polyfit(E_total, F_values, 1)
                N_from_slope = coeffs[0]
                
                # Calculate R²
                F_fit = coeffs[0] * E_total + coeffs[1]
                ss_res = np.sum((F_values - F_fit) ** 2)
                ss_tot = np.sum((F_values - np.mean(F_values)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                r_squared_dict[m] = r_squared
                
                # Plot fitted line
                E_line = np.linspace(min(E_total) * 0.9, max(E_total) * 1.1, 100)
                F_line = coeffs[0] * E_line + coeffs[1]
                ax.plot(E_line, F_line, 'r--', linewidth=2, 
                       label=f'N = {N_from_slope:,.0f} STB\nR² = {r_squared:.4f}')
            
            ax.set_xlabel(f'Eo + {m:.1f}*Eg (m3/m3 std)', fontsize=10)
            ax.set_ylabel('F (m3)', fontsize=10)
            ax.set_title(f'm = {m:.1f}', fontsize=12, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for idx in range(n_plots, len(axes)):
            axes[idx].axis('off')
        
        fig.suptitle('Gas Cap Size Determination: F vs (Eo + m*Eg)', 
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        return fig, axes, r_squared_dict
    
    def determine_optimal_m(self, 
                          production_data: ProductionData,
                          m_values: Optional[np.ndarray] = None,
                          We_values: Optional[np.ndarray] = None,
                          show_plot: bool = True) -> Tuple[float, dict]:
        """
        Determine the optimal gas cap size (m) by finding the m value that 
        produces the best linear fit (highest R²) in the F vs (Eo + m*Eg) plot.
        
        Args:
            production_data: ProductionData object with time series
            m_values: Array of m values to test (default: 0.1 to 0.9 in steps of 0.01)
            We_values: Water influx values for each time point (optional)
            show_plot: Whether to display a plot of R² vs m (default: True)
            
        Returns:
            Tuple of (optimal_m, results_dict)
            optimal_m: The m value with the highest R²
            results_dict: Dictionary with all m values and their R² values
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            if show_plot:
                raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")
        
        if m_values is None:
            m_values = np.arange(0.1, 1.0, 0.01)
        
        n_points = len(production_data.time)
        
        if We_values is None:
            We_values = production_data.We
        
        # Calculate F values (independent of m)
        F_values = np.zeros(n_points)
        for i in range(n_points):
            F_values[i] = self._calculate_withdrawal_terms(
                production_data.Np[i], production_data.Gp[i], production_data.Wp[i],
                production_data.pressure[i], Winj=production_data.Winj[i],
                Ginj=production_data.Ginj[i], We=We_values[i],
            )['F']
        
        # Calculate Eo and Eg for each pressure point
        Eo_values = np.zeros(n_points)
        Eg_values = np.zeros(n_points)
        
        for i in range(n_points):
            Eo, Eg, _ = self.calculate_expansion_terms(production_data.pressure[i])
            Eo_values[i] = Eo
            Eg_values[i] = Eg
        
        # Calculate R² for each m value
        r_squared_values = []
        
        for m in m_values:
            E_total = Eo_values + m * Eg_values
            
            if len(E_total) > 1:
                coeffs = np.polyfit(E_total, F_values, 1)
                F_fit = coeffs[0] * E_total + coeffs[1]
                ss_res = np.sum((F_values - F_fit) ** 2)
                ss_tot = np.sum((F_values - np.mean(F_values)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                r_squared_values.append(r_squared)
            else:
                r_squared_values.append(0)
        
        r_squared_values = np.array(r_squared_values)
        
        # Find optimal m
        optimal_idx = np.argmax(r_squared_values)
        optimal_m = m_values[optimal_idx]
        optimal_r_squared = r_squared_values[optimal_idx]
        
        results_dict = {
            'm_values': m_values,
            'r_squared_values': r_squared_values,
            'optimal_m': optimal_m,
            'optimal_r_squared': optimal_r_squared
        }
        
        # Create plot if requested
        if show_plot:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(m_values, r_squared_values, 'b-', linewidth=2)
            ax.scatter(optimal_m, optimal_r_squared, s=200, c='red', 
                      marker='*', zorder=5, label=f'Optimal m = {optimal_m:.3f}')
            ax.axvline(optimal_m, color='red', linestyle='--', alpha=0.5)
            ax.set_xlabel('Gas Cap Size Parameter, m', fontsize=12)
            ax.set_ylabel('Coefficient of Determination, R²', fontsize=12)
            ax.set_title('Optimal Gas Cap Size Determination', fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
        
        print(f"\nOptimal gas cap size parameter: m = {optimal_m:.3f}")
        print(f"Coefficient of determination: R² = {optimal_r_squared:.6f}")
        
        return optimal_m, results_dict
