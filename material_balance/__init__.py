"""
Material Balance Framework for Reservoir Engineering

This package provides tools to calculate initial volumes in-place (STOIIP/GIIP)
using material balance equations for oil and gas reservoirs.

Supports both metric and field (English) unit systems.
"""

__version__ = "1.0.0"
__author__ = "Petroleum Engineering Team"

from .oil_reservoir import OilReservoir
from .gas_reservoir import GasReservoir
from .pvt_properties import PVTProperties
from .units import UnitSystem, UnitConverter
from .input_reader import InputReader, create_template_files
from .darcy_flow import DarcyRadialFlow, DarcyFlowParameters, calculate_drainage_radius, calculate_skin_factor

__all__ = ['OilReservoir', 'GasReservoir', 'PVTProperties', 'UnitSystem', 'UnitConverter', 
           'InputReader', 'create_template_files', 'DarcyRadialFlow', 'DarcyFlowParameters',
           'calculate_drainage_radius', 'calculate_skin_factor']
