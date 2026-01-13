"""
Unit System Conversion Module

This module provides unit conversion functionality to support both
metric and field (English) unit systems in the material balance framework.

Internal calculations use metric units (SI-based):
- Pressure: kgf/cm²
- Volume: m³ std
- Temperature: K (Kelvin)
- FVF: m³/m³ std
- GOR: m³/m³ std
- Compressibility: 1/(kgf/cm²)

Field units (US petroleum):
- Pressure: psia
- Volume: STB (oil/water), SCF (gas)
- Temperature: °F (Fahrenheit)
- FVF: rb/STB, rb/SCF
- GOR: SCF/STB
- Compressibility: 1/psi
"""

from enum import Enum
from typing import Union, List
import numpy as np


class UnitSystem(Enum):
    """Enumeration for supported unit systems"""
    METRIC = "metric"  # SI-based metric units (m³, kgf/cm², °C, K)
    FIELD = "field"    # US petroleum field units (STB, SCF, psia, °F)


class UnitConverter:
    """
    Unit conversion class for petroleum engineering calculations.
    
    Handles bidirectional conversions between metric and field units.
    All internal calculations use metric units.
    """
    
    # Conversion factors (from field to metric)
    PSIA_TO_KGFCM2 = 0.0703069  # 1 psia = 0.0703069 kgf/cm²
    KGFCM2_TO_PSIA = 14.2233    # 1 kgf/cm² = 14.2233 psia
    
    STB_TO_M3 = 0.158987        # 1 STB = 0.158987 m³ std
    M3_TO_STB = 6.28981         # 1 m³ std = 6.28981 STB
    
    SCF_TO_M3 = 0.0283168       # 1 SCF = 0.0283168 m³ std
    M3_TO_SCF = 35.3147         # 1 m³ std = 35.3147 SCF
    
    RB_TO_M3 = 0.158987         # 1 rb = 0.158987 m³
    M3_TO_RB = 6.28981          # 1 m³ = 6.28981 rb
    
    # GOR conversion: SCF/STB to m³/m³
    SCFSTB_TO_M3M3 = SCF_TO_M3 / STB_TO_M3  # ≈ 0.178107
    M3M3_TO_SCFSTB = M3_TO_SCF / M3_TO_STB  # ≈ 5.61458
    
    @staticmethod
    def to_array(value: Union[float, List, np.ndarray]) -> np.ndarray:
        """Convert input to numpy array"""
        if isinstance(value, (list, tuple)):
            return np.array(value)
        elif isinstance(value, np.ndarray):
            return value
        else:
            return np.array([value])
    
    @staticmethod
    def to_scalar_if_single(arr: np.ndarray) -> Union[float, np.ndarray]:
        """Convert single-element array to scalar"""
        if arr.size == 1:
            return float(arr[0])
        return arr
    
    # ========== Pressure Conversions ==========
    
    @classmethod
    def pressure_to_metric(cls, pressure: Union[float, List, np.ndarray], 
                          from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert pressure to metric (kgf/cm²)"""
        p = cls.to_array(pressure)
        if from_system == UnitSystem.FIELD:
            result = p * cls.PSIA_TO_KGFCM2
        else:
            result = p
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def pressure_from_metric(cls, pressure: Union[float, List, np.ndarray],
                            to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert pressure from metric (kgf/cm²) to target system"""
        p = cls.to_array(pressure)
        if to_system == UnitSystem.FIELD:
            result = p * cls.KGFCM2_TO_PSIA
        else:
            result = p
        return cls.to_scalar_if_single(result)
    
    # ========== Volume Conversions ==========
    
    @classmethod
    def oil_volume_to_metric(cls, volume: Union[float, List, np.ndarray],
                            from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert oil/water volume to metric (m³ std)"""
        v = cls.to_array(volume)
        if from_system == UnitSystem.FIELD:
            result = v * cls.STB_TO_M3
        else:
            result = v
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def oil_volume_from_metric(cls, volume: Union[float, List, np.ndarray],
                              to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert oil/water volume from metric (m³ std) to target system"""
        v = cls.to_array(volume)
        if to_system == UnitSystem.FIELD:
            result = v * cls.M3_TO_STB
        else:
            result = v
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def gas_volume_to_metric(cls, volume: Union[float, List, np.ndarray],
                            from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert gas volume to metric (m³ std)"""
        v = cls.to_array(volume)
        if from_system == UnitSystem.FIELD:
            result = v * cls.SCF_TO_M3
        else:
            result = v
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def gas_volume_from_metric(cls, volume: Union[float, List, np.ndarray],
                              to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert gas volume from metric (m³ std) to target system"""
        v = cls.to_array(volume)
        if to_system == UnitSystem.FIELD:
            result = v * cls.M3_TO_SCF
        else:
            result = v
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def reservoir_volume_to_metric(cls, volume: Union[float, List, np.ndarray],
                                   from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert reservoir volume to metric (m³)"""
        v = cls.to_array(volume)
        if from_system == UnitSystem.FIELD:
            result = v * cls.RB_TO_M3
        else:
            result = v
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def reservoir_volume_from_metric(cls, volume: Union[float, List, np.ndarray],
                                    to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert reservoir volume from metric (m³) to target system"""
        v = cls.to_array(volume)
        if to_system == UnitSystem.FIELD:
            result = v * cls.M3_TO_RB
        else:
            result = v
        return cls.to_scalar_if_single(result)
    
    # ========== Temperature Conversions ==========
    
    @classmethod
    def temperature_to_kelvin(cls, temp: float, from_system: UnitSystem) -> float:
        """Convert temperature to Kelvin"""
        if from_system == UnitSystem.FIELD:
            # °F to K: K = (°F - 32) * 5/9 + 273.15
            celsius = (temp - 32) * 5 / 9
            return celsius + 273.15
        else:
            # Assume input is °C, convert to K
            return temp + 273.15
    
    @classmethod
    def temperature_from_kelvin(cls, temp_k: float, to_system: UnitSystem) -> float:
        """Convert temperature from Kelvin to target system"""
        if to_system == UnitSystem.FIELD:
            # K to °F: °F = (K - 273.15) * 9/5 + 32
            celsius = temp_k - 273.15
            return celsius * 9 / 5 + 32
        else:
            # K to °C
            return temp_k - 273.15
    
    # ========== Formation Volume Factor Conversions ==========
    
    @classmethod
    def bo_to_metric(cls, bo: Union[float, List, np.ndarray],
                    from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert oil FVF to metric (m³/m³ std)"""
        b = cls.to_array(bo)
        if from_system == UnitSystem.FIELD:
            # rb/STB to m³/m³: same numerical value (both are reservoir/standard ratios)
            result = b
        else:
            result = b
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def bo_from_metric(cls, bo: Union[float, List, np.ndarray],
                      to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert oil FVF from metric (m³/m³ std) to target system"""
        b = cls.to_array(bo)
        if to_system == UnitSystem.FIELD:
            # m³/m³ to rb/STB: same numerical value
            result = b
        else:
            result = b
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def bg_to_metric(cls, bg: Union[float, List, np.ndarray],
                    from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert gas FVF to metric (m³/m³ std)"""
        b = cls.to_array(bg)
        if from_system == UnitSystem.FIELD:
            # rb/SCF to m³/m³: need to convert
            # rb/SCF * (m³/rb) / (m³/SCF) = m³/m³
            result = b * cls.RB_TO_M3 / cls.SCF_TO_M3
        else:
            result = b
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def bg_from_metric(cls, bg: Union[float, List, np.ndarray],
                      to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert gas FVF from metric (m³/m³ std) to target system"""
        b = cls.to_array(bg)
        if to_system == UnitSystem.FIELD:
            # m³/m³ to rb/SCF: reverse conversion
            result = b * cls.SCF_TO_M3 / cls.RB_TO_M3
        else:
            result = b
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def bw_to_metric(cls, bw: Union[float, List, np.ndarray],
                    from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert water FVF to metric (m³/m³ std)"""
        b = cls.to_array(bw)
        if from_system == UnitSystem.FIELD:
            # rb/STB to m³/m³: same numerical value
            result = b
        else:
            result = b
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def bw_from_metric(cls, bw: Union[float, List, np.ndarray],
                      to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert water FVF from metric (m³/m³ std) to target system"""
        b = cls.to_array(bw)
        if to_system == UnitSystem.FIELD:
            # m³/m³ to rb/STB: same numerical value
            result = b
        else:
            result = b
        return cls.to_scalar_if_single(result)
    
    # ========== Gas-Oil Ratio Conversions ==========
    
    @classmethod
    def rs_to_metric(cls, rs: Union[float, List, np.ndarray],
                    from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert solution GOR to metric (m³/m³ std)"""
        r = cls.to_array(rs)
        if from_system == UnitSystem.FIELD:
            # SCF/STB to m³/m³
            result = r * cls.SCFSTB_TO_M3M3
        else:
            result = r
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def rs_from_metric(cls, rs: Union[float, List, np.ndarray],
                      to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert solution GOR from metric (m³/m³ std) to target system"""
        r = cls.to_array(rs)
        if to_system == UnitSystem.FIELD:
            # m³/m³ to SCF/STB
            result = r * cls.M3M3_TO_SCFSTB
        else:
            result = r
        return cls.to_scalar_if_single(result)
    
    # ========== Compressibility Conversions ==========
    
    @classmethod
    def compressibility_to_metric(cls, comp: Union[float, List, np.ndarray],
                                  from_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert compressibility to metric (1/(kgf/cm²))"""
        c = cls.to_array(comp)
        if from_system == UnitSystem.FIELD:
            # 1/psi to 1/(kgf/cm²)
            # 1/psi * (psi/kgf/cm²) = 1/(kgf/cm²)
            result = c * cls.KGFCM2_TO_PSIA
        else:
            result = c
        return cls.to_scalar_if_single(result)
    
    @classmethod
    def compressibility_from_metric(cls, comp: Union[float, List, np.ndarray],
                                   to_system: UnitSystem) -> Union[float, np.ndarray]:
        """Convert compressibility from metric (1/(kgf/cm²)) to target system"""
        c = cls.to_array(comp)
        if to_system == UnitSystem.FIELD:
            # 1/(kgf/cm²) to 1/psi
            result = c * cls.PSIA_TO_KGFCM2
        else:
            result = c
        return cls.to_scalar_if_single(result)
