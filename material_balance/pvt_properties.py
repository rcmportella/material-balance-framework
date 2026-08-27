"""
PVT (Pressure-Volume-Temperature) Properties Module

This module provides classes and functions to handle fluid properties
required for material balance calculations.
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from .units import UnitSystem, UnitConverter


@dataclass
class PVTProperties:
    """
    Container for PVT properties at different pressure points.
    
    All properties should be provided as arrays or lists corresponding to
    different pressure measurements.
    
    Input units depend on unit_system parameter:
    - METRIC: pressure (kgf/cm²), Bo/Bw (m³/m³ std), Bg (m³/m³ std), 
              Rs (m³/m³ std), compressibility (1/(kgf/cm²))
    - FIELD: pressure (psia), Bo/Bw (rb/STB), Bg (rb/SCF), 
             Rs (SCF/STB), compressibility (1/psi)
    
    Internally, all data is stored in metric units.
    """
    
    # Pressure array
    pressure: np.ndarray
    
    # Unit system for input data (default: METRIC)
    unit_system: UnitSystem = UnitSystem.METRIC
    
    # Oil properties
    Bo: Optional[np.ndarray] = None  # Oil formation volume factor (m3/m3 std)
    Rs: Optional[np.ndarray] = None  # Solution gas-oil ratio (m3/m3 std)
    co: Optional[np.ndarray] = None  # Oil compressibility (1/(kgf/cm2))
    
    # Gas properties
    Bg: Optional[np.ndarray] = None  # Gas formation volume factor (m3/m3 std)
    z: Optional[np.ndarray] = None   # Gas compressibility factor (dimensionless)
    cg: Optional[np.ndarray] = None  # Gas compressibility (1/(kgf/cm2))
    
    # Water properties
    Bw: Optional[np.ndarray] = None  # Water formation volume factor (m3/m3 std)
    cw: Optional[np.ndarray] = None  # Water compressibility (1/(kgf/cm2))
    
    # Rock properties
    cf: Optional[np.ndarray] = None  # Formation compressibility (1/(kgf/cm2))
    
    def __post_init__(self):
        """Convert lists to numpy arrays and convert to metric units if needed"""
        converter = UnitConverter()
        
        # Convert pressure
        self.pressure = np.array(self.pressure)
        self.pressure = converter.pressure_to_metric(self.pressure, self.unit_system)
        
        # Convert each property to numpy array and metric units
        for attr in ['Bo', 'Rs', 'co', 'Bg', 'z', 'cg', 'Bw', 'cw', 'cf']:
            value = getattr(self, attr)
            if value is not None:
                value = np.array(value)
                
                # Apply unit conversion based on property type
                if self.unit_system == UnitSystem.FIELD:
                    if attr == 'Bo':
                        value = converter.bo_to_metric(value, self.unit_system)
                    elif attr == 'Bg':
                        value = converter.bg_to_metric(value, self.unit_system)
                    elif attr == 'Bw':
                        value = converter.bw_to_metric(value, self.unit_system)
                    elif attr == 'Rs':
                        value = converter.rs_to_metric(value, self.unit_system)
                    elif attr in ['co', 'cg', 'cw', 'cf']:
                        value = converter.compressibility_to_metric(value, self.unit_system)
                    # 'z' is dimensionless, no conversion needed
                
                setattr(self, attr, value)
        
        # After conversion, all internal data is in metric units
        self.unit_system = UnitSystem.METRIC
    
    def interpolate_property(self, property_name: str, target_pressure: float) -> float:
        """
        Interpolate a PVT property at a target pressure.
        
        Args:
            property_name: Name of the property to interpolate ('Bo', 'Rs', etc.)
            target_pressure: Pressure at which to interpolate
            
        Returns:
            Interpolated property value
        """
        prop_values = getattr(self, property_name)
        
        if prop_values is None:
            raise ValueError(f"Property {property_name} is not defined")
        
        # Check if pressure array is in decreasing order
        # np.interp requires x-coordinates to be in increasing order
        if len(self.pressure) > 1 and self.pressure[0] > self.pressure[-1]:
            # Reverse both arrays for interpolation
            return np.interp(target_pressure, self.pressure[::-1], prop_values[::-1])
        else:
            # Pressure is already in increasing order
            return np.interp(target_pressure, self.pressure, prop_values)
    
    def get_properties_at_pressure(self, target_pressure: float) -> dict:
        """
        Get all available PVT properties interpolated at target pressure.
        
        Args:
            target_pressure: Pressure at which to get properties
            
        Returns:
            Dictionary with interpolated properties
        """
        result = {'pressure': target_pressure}
        
        for attr in ['Bo', 'Rs', 'co', 'Bg', 'z', 'cg', 'Bw', 'cw', 'cf']:
            value = getattr(self, attr)
            if value is not None:
                result[attr] = self.interpolate_property(attr, target_pressure)
        
        return result


class CorrelationsPVT:
    """
    Class providing common PVT correlations for cases where measured data is not available.
    """
    
    @staticmethod
    def standing_Bo(Rs: float, gamma_g: float, gamma_o: float, T: float) -> float:
        """
        Standing correlation for oil formation volume factor.
        
        Args:
            Rs: Solution GOR (m3/m3 std)
            gamma_g: Gas specific gravity (air=1)
            gamma_o: Oil specific gravity (water=1)
            T: Temperature (°C)
            
        Returns:
            Bo: Oil formation volume factor (m3/m3 std)
        """
        T_F = T * 9/5 + 32  # Convert to Fahrenheit for correlation
        Rs_scf_stb = Rs / 0.178107  # Convert m3/m3 to scf/stb
        F = Rs_scf_stb * (gamma_g / gamma_o)**0.5 + 1.25 * T_F
        Bo = 0.9759 + 0.00012 * F**1.2
        return Bo
    
    @staticmethod
    def standing_Rs(P: float, gamma_g: float, gamma_o: float, T: float) -> float:
        """
        Standing correlation for solution gas-oil ratio.
        
        Args:
            P: Pressure (kgf/cm2)
            gamma_g: Gas specific gravity (air=1)
            gamma_o: Oil specific gravity (water=1)
            T: Temperature (°C)
            
        Returns:
            Rs: Solution GOR (m3/m3 std)
        """
        P_psia = P * 14.2233  # Convert to psia
        T_F = T * 9/5 + 32  # Convert to Fahrenheit
        # Standing returns Rs in SCF/STB. Convert it using
        # 1 SCF/STB = 0.178107 m3/m3 std.
        API = 141.5 / gamma_o - 131.5
        x = (P_psia / 18.2 + 1.4) * 10**(0.0125 * API - 0.00091 * T_F)
        Rs_scf_stb = gamma_g * x**1.2048
        Rs = Rs_scf_stb * 0.178107  # Convert scf/stb to m3/m3
        return Rs
    
    @staticmethod
    def gas_z_factor_hall_yarborough(P: float, T: float, gamma_g: float) -> float:
        """
        Hall-Yarborough correlation for gas compressibility factor.
        
        Args:
            P: Pressure (kgf/cm2)
            T: Temperature (K)
            gamma_g: Gas specific gravity (air=1)
            
        Returns:
            z: Gas compressibility factor (dimensionless)
        """
        # Convert to field units for correlation
        P_psia = P * 14.2233
        T_R = T * 1.8  # K to Rankine
        
        # Pseudo-critical properties
        Tpc = 168 + 325 * gamma_g - 12.5 * gamma_g**2
        Ppc = 677 + 15.0 * gamma_g - 37.5 * gamma_g**2
        
        # Pseudo-reduced properties
        Tpr = T_R / Tpc
        Ppr = P_psia / Ppc
        
        # Initial guess
        y = 0.001
        t = 1 / Tpr

        # Newton-Raphson iteration
        for _ in range(20):
            A = 0.06125 * Ppr * t * np.exp(-1.2 * (1 - t)**2)
            B = 14.76 * t - 9.76 * t**2 + 4.58 * t**3
            C = 90.7 * t - 242.2 * t**2 + 42.4 * t**3
            D = 2.18 + 2.82 * t
            
            F = -A + (y + y**2 + y**3 - y**4) / (1 - y)**3 - B*y**2 + C*y**D
            dF = (1 + 4*y + 4*y**2 - 4*y**3 + y**4) / (1 - y)**4 - 2*B*y + C*D*y**(D-1)
            
            y_new = y - F / dF
            
            if abs(y_new - y) < 1e-6:
                y = y_new
                break
            y = y_new
        
        z = A / y
        return z
    
    @staticmethod
    def gas_Bg(P: float, T: float, z: float) -> float:
        """
        Calculate gas formation volume factor.
        
        Args:
            P: Pressure (kgf/cm2)
            T: Temperature (K)
            z: Gas compressibility factor
            
        Returns:
            Bg: Gas formation volume factor (m3/m3 std)
        """
        # Bg = z * R * T / P, where R = 0.00829 for metric units (m3·kgf/cm2)/(mol·K)
        # At standard conditions: P_sc = 1.0332 kgf/cm2, T_sc = 288.15 K
        Bg = 0.00351 * z * T / P  # Simplified coefficient for metric units
        return Bg

    @staticmethod
    def gas_viscosity_lee_gonzalez_eakin(P: float, T: float, gamma_g: float, z: float) -> float:
        """
        Lee-Gonzalez-Eakin correlation for natural gas viscosity.

        Args:
            P: Pressure (kgf/cm2)
            T: Temperature (K)
            gamma_g: Gas specific gravity (air=1)
            z: Gas compressibility factor (dimensionless)

        Returns:
            mu_g: Gas viscosity (cP)
        """
        # Convert to field units for correlation
        P_psia = P * 14.2233
        T_R = T * 1.8

        MW_g = gamma_g * 28.97  # lb/lbmol
        rho_g = (P_psia * MW_g) / (z * 10.73 * T_R)  # lb/ft3

        Kv = (9.379 + 0.01607 * MW_g) * T_R**1.5 / (209.2 + 19.26 * MW_g + T_R)
        Xv = 3.448 + 986.4 / T_R + 0.01009 * MW_g
        Yv = 2.447 - 0.2224 * Xv

        mu_g = 1e-4 * Kv * np.exp(Xv * (rho_g / 62.4)**Yv)
        return mu_g

    @staticmethod
    def oil_viscosity_beggs_robinson(API: float, T: float, Rs: float) -> float:
        """
        Beggs-Robinson correlation for saturated (dead + live) oil viscosity.

        Args:
            API: Oil API gravity
            T: Temperature (°C)
            Rs: Solution GOR (m3/m3 std)

        Returns:
            mu_ob: Saturated oil viscosity (cP)
        """
        # Convert to field units for correlation
        T_F = T * 9 / 5 + 32
        T_R = T_F + 459.67
        Rs_scf_stb = Rs / 0.178107

        # Dead oil viscosity
        Z = 3.0324 - 0.02023 * API
        Y = 10**Z
        x = Y * (T_R - 460)**(-1.163)
        mu_od = 10**x - 1

        # Saturated oil viscosity
        a = 10.715 * (Rs_scf_stb + 100)**(-0.515)
        b = 5.44 * (Rs_scf_stb + 150)**(-0.338)
        mu_ob = a * mu_od**b
        return mu_ob
    
    @staticmethod
    def vasquez_beggs_Bo(Rs: float, gamma_g: float, gamma_o: float, T: float, P: float, 
                        API: float, separator_pressure: float = 7.03) -> float:
        """
        Vasquez-Beggs correlation for oil formation volume factor.
        More accurate than Standing for many cases.
        
        Args:
            Rs: Solution GOR (m3/m3 std)
            gamma_g: Gas specific gravity at separator (air=1)
            gamma_o: Oil specific gravity (water=1)
            T: Temperature (°C)
            P: Pressure (kgf/cm2)
            API: Oil API gravity
            separator_pressure: Separator pressure (kgf/cm2, default ~100 psia)
            
        Returns:
            Bo: Oil formation volume factor (m3/m3 std)
        """
        # Convert to field units
        T_F = T * 9/5 + 32
        Rs_scf_stb = Rs / 0.178107
        sep_p_psia = separator_pressure * 14.2233
        
        # Correct gas gravity to 100 psi separator
        gamma_gs = gamma_g * (1 + 5.912e-5 * API * T_F * np.log10(sep_p_psia / 114.7))
        
        if API <= 30:
            C1, C2, C3 = 0.0004677, 1.751e-5, -1.811e-8
        else:
            C1, C2, C3 = 0.000467, 1.100e-5, 1.337e-9
        
        Bo = 1.0 + C1 * Rs_scf_stb + (T_F - 60) * (API / gamma_gs) * (C2 + C3 * Rs_scf_stb)
        return Bo

    @staticmethod
    def vasquez_beggs_co(P: float, Rs: float, gamma_g: float, API: float, T: float) -> float:
        """Calculate oil compressibility using the Vasquez-Beggs correlation.

        Inputs use the metric conventions of this module: pressure in kgf/cm2,
        solution GOR in m3/m3 std and temperature in degrees C. The result is
        returned in 1/(kgf/cm2).
        """
        if P <= 0 or Rs < 0 or gamma_g <= 0 or API <= 0:
            raise ValueError("P, Rs, gamma_g and API must be positive values.")

        pressure_psia = P * 14.2233
        rs_scf_stb = Rs / 0.178107
        temperature_f = T * 9 / 5 + 32
        numerator = -1433 + 5 * rs_scf_stb + 17.2 * temperature_f - 1180 * gamma_g + 12.61 * API
        compressibility_psi = numerator / (100000 * pressure_psia)
        return compressibility_psi * 14.2233

    @staticmethod
    def vasquez_beggs_oil_pvt(
        pressures: np.ndarray,
        temperature_c: float,
        bubble_point_pressure: float,
        gamma_g: float,
        API: float,
    ) -> dict[str, np.ndarray]:
        """Calculate saturated and undersaturated oil PVT properties.

        Below or at the bubble point, Standing Rs and Vasquez-Beggs Bo are
        used. Above the bubble point, Rs remains equal to Rsb and Bo is
        calculated from the traditional compressibility relation, integrated
        from Bob at the bubble point. Returned arrays are ordered like
        ``pressures`` and use metric units.
        """
        pressure_array = np.asarray(pressures, dtype=float)
        if pressure_array.ndim != 1 or pressure_array.size == 0:
            raise ValueError("pressures must be a non-empty one-dimensional array.")
        if bubble_point_pressure <= 0:
            raise ValueError("bubble_point_pressure must be greater than zero.")
        if API <= 0 or API > 100 or gamma_g <= 0:
            raise ValueError("API must be between 0 and 100, and gamma_g must be positive.")

        gamma_o = 141.5 / (API + 131.5)

        rs_at_bubble = CorrelationsPVT.standing_Rs(
            bubble_point_pressure, gamma_g, gamma_o, temperature_c
        )
        bo_at_bubble = CorrelationsPVT.vasquez_beggs_Bo(
            rs_at_bubble, gamma_g, gamma_o, temperature_c, bubble_point_pressure, API
        )

        rs_values = np.empty_like(pressure_array)
        bo_values = np.empty_like(pressure_array)
        co_values = np.empty_like(pressure_array)
        saturated = pressure_array <= bubble_point_pressure

        for index, pressure in enumerate(pressure_array):
            if saturated[index]:
                rs_values[index] = CorrelationsPVT.standing_Rs(
                    pressure, gamma_g, gamma_o, temperature_c
                )
                bo_values[index] = CorrelationsPVT.vasquez_beggs_Bo(
                    rs_values[index], gamma_g, gamma_o, temperature_c, pressure, API
                )
            else:
                rs_values[index] = rs_at_bubble
            co_values[index] = CorrelationsPVT.vasquez_beggs_co(
                pressure, rs_values[index], gamma_g, API, temperature_c
            )

        above_indices = np.flatnonzero(~saturated)
        if above_indices.size:
            above_pressures = pressure_array[above_indices]
            order = np.argsort(above_pressures)
            sorted_pressures = above_pressures[order]
            sorted_co = co_values[above_indices][order]
            integration_pressures = np.concatenate(([bubble_point_pressure], sorted_pressures))
            integration_co = np.concatenate((
                [CorrelationsPVT.vasquez_beggs_co(
                    bubble_point_pressure, rs_at_bubble, gamma_g, API, temperature_c
                )],
                sorted_co,
            ))
            expansion = np.zeros(integration_pressures.size)
            expansion[1:] = np.cumsum(
                0.5 * (integration_co[1:] + integration_co[:-1])
                * np.diff(integration_pressures)
            )
            bo_values[above_indices[order]] = bo_at_bubble * np.exp(-expansion[1:])

        return {
            "Rs": rs_values,
            "Bo": bo_values,
            "co": co_values,
            "Rsb": np.array([rs_at_bubble]),
            "Bob": np.array([bo_at_bubble]),
        }
