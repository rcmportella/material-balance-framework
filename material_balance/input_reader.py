"""
Input Reader Module

This module provides functions to read reservoir and production data from external files.
Supports CSV files for tabular data and JSON files for configuration data.

Users can prepare their input files in Excel (save as CSV) or any text editor.
"""

import json
import csv
import unicodedata
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
from .pvt_properties import PVTProperties
from .oil_reservoir import ProductionData, OilReservoir
from .gas_reservoir import GasProductionData, GasReservoir
from .units import UnitSystem


class InputReader:
    """
    Read reservoir input data from external files.
    
    Supports:
    - PVT properties from CSV files
    - Production history from CSV files
    - Reservoir configuration from JSON files
    """

    @staticmethod
    def _detect_csv_delimiter(filepath: Path) -> str:
        with filepath.open('r', encoding='utf-8-sig', newline='') as csv_file:
            sample = csv_file.read(8192)
        try:
            return csv.Sniffer().sniff(sample, delimiters=',;').delimiter
        except csv.Error:
            return ','
    
    @staticmethod
    def read_pvt_from_csv(filepath: str, unit_system: UnitSystem = UnitSystem.METRIC) -> PVTProperties:
        """
        Read PVT properties from a CSV file.
        
        Expected CSV format:
        Header row with column names: pressure, Bo, Rs, Bg, Bw, cw, cf, etc.
        Data rows with numerical values
        
        Example CSV:
        pressure,Bo,Rs,Bg,Bw,cw,cf
        3330,1.2511,510,0.00087,1.02,3e-6,4e-6
        3150,1.2353,477,0.00092,1.02,3e-6,4e-6
        
        Args:
            filepath: Path to the CSV file
            unit_system: Unit system of the data (METRIC or FIELD)
            
        Returns:
            PVTProperties object with data from the file
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"PVT file not found: {filepath}")
        
        # Read CSV file
        data = {}
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=InputReader._detect_csv_delimiter(filepath))
            for row in reader:
                if not row or all(
                    not value or value.strip().startswith('#')
                    for value in row.values()
                ):
                    continue
                for key, value in row.items():
                    key = key.strip()
                    if key not in data:
                        data[key] = []
                    # Handle empty values
                    if value.strip():
                        data[key].append(float(value))
                    else:
                        data[key].append(None)
        
        # Convert to numpy arrays, handling None values
        for key in data:
            data[key] = np.array(data[key])
        
        # Check for required pressure column
        if 'pressure' not in data:
            raise ValueError("CSV file must contain a 'pressure' column")
        
        # Create PVTProperties object
        pvt_kwargs = {
            'pressure': data['pressure'],
            'unit_system': unit_system
        }
        
        # Add optional properties if they exist
        for prop in ['Bo', 'Rs', 'co', 'Bg', 'z', 'cg', 'Bw', 'cw', 'cf']:
            if prop in data:
                pvt_kwargs[prop] = data[prop]
        
        return PVTProperties(**pvt_kwargs)

    @staticmethod
    def read_pvt_from_excel(filepath: str, unit_system: UnitSystem = UnitSystem.METRIC) -> PVTProperties:
        """Read the PVT worksheet exported by ``PVT_table.py``."""
        from openpyxl import load_workbook

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"PVT file not found: {filepath}")

        workbook = load_workbook(filepath, read_only=True, data_only=True)
        try:
            sheet = workbook['PVT'] if 'PVT' in workbook.sheetnames else workbook.active
            headers = list(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ()))

            def normalize_header(value: Any) -> str:
                text = unicodedata.normalize('NFKD', str(value or ''))
                text = ''.join(char for char in text if not unicodedata.combining(char))
                return text.split('(', 1)[0].strip().casefold().replace(' ', '_')

            aliases = {
                'pressure': 'pressure', 'pressao': 'pressure',
                'bo': 'Bo', 'bg': 'Bg', 'rs': 'Rs', 'z': 'z', 'co': 'co',
                'bw': 'Bw', 'cw': 'cw', 'cf': 'cf', 'cg': 'cg',
            }
            columns = {
                index: aliases[normalize_header(header)]
                for index, header in enumerate(headers)
                if normalize_header(header) in aliases
            }
            if 'pressure' not in columns.values():
                raise ValueError("PVT Excel sheet must contain a pressure column")

            values_by_property = {name: [] for name in columns.values()}
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not row or all(value is None for value in row):
                    continue
                for index, name in columns.items():
                    value = row[index] if index < len(row) else None
                    if value is None:
                        raise ValueError(f"PVT Excel column '{name}' contains an empty value")
                    values_by_property[name].append(float(value))

            if not values_by_property.get('pressure'):
                raise ValueError("PVT Excel sheet contains no data rows")
            if not {'Bo', 'Rs'}.issubset(values_by_property):
                raise ValueError("PVT Excel sheet must contain Bo and Rs columns")

            workbook_unit_system = unit_system
            if 'Parâmetros' in workbook.sheetnames:
                parameter_sheet = workbook['Parâmetros']
                for label, value in parameter_sheet.iter_rows(min_col=1, max_col=2, values_only=True):
                    normalized_label = normalize_header(label)
                    if normalized_label == 'sistema_de_unidades' and value:
                        workbook_unit_system = UnitSystem[str(value).strip().upper()]
                        break

            pressure_header = str(headers[next(
                index for index, name in columns.items() if name == 'pressure'
            )]).casefold()
            if 'bar' in pressure_header:
                values_by_property['pressure'] = [value / 0.980665 for value in values_by_property['pressure']]
                if 'co' in values_by_property:
                    values_by_property['co'] = [value * 0.980665 for value in values_by_property['co']]

            return PVTProperties(
                pressure=values_by_property.pop('pressure'),
                unit_system=workbook_unit_system,
                **values_by_property,
            )
        finally:
            workbook.close()

    @staticmethod
    def read_pvt_from_file(filepath: str, unit_system: UnitSystem = UnitSystem.METRIC) -> PVTProperties:
        """Read PVT data from CSV or the Excel format exported by ``PVT_table.py``."""
        suffix = Path(filepath).suffix.casefold()
        if suffix == '.csv':
            return InputReader.read_pvt_from_csv(filepath, unit_system)
        if suffix in {'.xlsx', '.xlsm'}:
            return InputReader.read_pvt_from_excel(filepath, unit_system)
        raise ValueError("PVT file must be a CSV, XLSX, or XLSM file")
    
    @staticmethod
    def read_production_from_csv(filepath: str, 
                                  unit_system: UnitSystem = UnitSystem.METRIC,
                                  reservoir_type: str = 'oil') -> Any:
        """
        Read production history from a CSV file.
        
        Expected CSV format for oil reservoir:
        time,Np,Gp,Wp,pressure,Winj,Ginj,We
        0,0,0,0,3330,0,0,0
        365,3295000,3459750000,0,3150,1000,0,0
        
        Expected CSV format for gas reservoir:
        time,Gp,Wp,pressure
        0,0,0,3330
        365,1000000,0,3150
        
        Args:
            filepath: Path to the CSV file
            unit_system: Unit system of the data (METRIC or FIELD)
            reservoir_type: Type of reservoir ('oil' or 'gas')
            
        Returns:
            ProductionData or GasProductionData object
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Production file not found: {filepath}")
        
        # Read CSV file
        data = {}
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=InputReader._detect_csv_delimiter(filepath))
            for row in reader:
                if not row or all(
                    not value or value.strip().startswith('#')
                    for value in row.values()
                ):
                    continue
                for key, value in row.items():
                    key = key.strip()
                    if key not in data:
                        data[key] = []
                    if value.strip():
                        data[key].append(float(value))
                    else:
                        data[key].append(0.0)
        
        # Convert to numpy arrays
        for key in data:
            data[key] = np.array(data[key])
        
        # Create production data object based on reservoir type
        if reservoir_type.lower() == 'oil':
            return ProductionData(
                time=data.get('time', np.arange(len(data['pressure']))),
                Np=data.get('Np', np.zeros(len(data['pressure']))),
                Gp=data.get('Gp', np.zeros(len(data['pressure']))),
                Wp=data.get('Wp', np.zeros(len(data['pressure']))),
                pressure=data['pressure'],
                unit_system=unit_system,
                Winj=data.get('Winj'),
                Ginj=data.get('Ginj'),
                We=data.get('We'),
            )
        elif reservoir_type.lower() == 'gas':
            return GasProductionData(
                time=data.get('time', np.arange(len(data['pressure']))),
                Gp=data['Gp'],
                Wp=data.get('Wp', np.zeros(len(data['pressure']))),
                pressure=data['pressure'],
                unit_system=unit_system
            )
        else:
            raise ValueError(f"Unknown reservoir type: {reservoir_type}")
    
    @staticmethod
    def read_config_from_json(filepath: str) -> Dict[str, Any]:
        """
        Read reservoir configuration from a JSON file.
        
        Expected JSON format:
        {
            "unit_system": "FIELD",
            "reservoir_type": "oil",
            "initial_pressure": 3330,
            "reservoir_temperature": 180,
            "initial_water_saturation": 0.2,
            "porosity": 0.18,
            "m": 0.54,
            "aquifer_influx": false,
            "aquifer_constant": 0
        }
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Dictionary with configuration parameters
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        # Convert unit_system string to enum if present
        if 'unit_system' in config:
            if isinstance(config['unit_system'], str):
                config['unit_system'] = UnitSystem[config['unit_system'].upper()]
        
        return config
    
    @staticmethod
    def create_oil_reservoir_from_files(pvt_file: str, 
                                         production_file: str,
                                         config_file: str) -> tuple:
        """
        Create an OilReservoir object and production data from input files.
        
        Args:
            pvt_file: Path to PVT properties CSV file
            production_file: Path to production history CSV file
            config_file: Path to configuration JSON file
            
        Returns:
            Tuple of (OilReservoir, ProductionData)
        """
        # Read configuration
        config = InputReader.read_config_from_json(config_file)
        unit_system = config.get('unit_system', UnitSystem.METRIC)
        
        # Read PVT properties
        pvt = InputReader.read_pvt_from_file(pvt_file, unit_system)
        
        # Read production data
        production = InputReader.read_production_from_csv(
            production_file, 
            unit_system, 
            reservoir_type='oil'
        )
        
        # Create reservoir object
        reservoir_kwargs = {
            'pvt_properties': pvt,
            'initial_pressure': config['initial_pressure'],
            'reservoir_temperature': config.get('reservoir_temperature', 25),
            'unit_system': unit_system
        }
        
        # Add optional parameters that OilReservoir actually accepts
        if 'm' in config:
            reservoir_kwargs['m'] = config['m']
        if 'aquifer_influx' in config:
            reservoir_kwargs['aquifer_influx'] = config['aquifer_influx']
        
        reservoir = OilReservoir(**reservoir_kwargs)
        
        return reservoir, production
    
    @staticmethod
    def create_gas_reservoir_from_files(pvt_file: str, 
                                         production_file: str,
                                         config_file: str) -> tuple:
        """
        Create a GasReservoir object and production data from input files.
        
        Args:
            pvt_file: Path to PVT properties CSV file
            production_file: Path to production history CSV file
            config_file: Path to configuration JSON file
            
        Returns:
            Tuple of (GasReservoir, GasProductionData)
        """
        # Read configuration
        config = InputReader.read_config_from_json(config_file)
        unit_system = config.get('unit_system', UnitSystem.METRIC)
        
        # Read PVT properties
        pvt = InputReader.read_pvt_from_csv(pvt_file, unit_system)
        
        # Read production data
        production = InputReader.read_production_from_csv(
            production_file, 
            unit_system, 
            reservoir_type='gas'
        )
        
        # Create reservoir object
        reservoir_kwargs = {
            'pvt_properties': pvt,
            'initial_pressure': config['initial_pressure'],
            'reservoir_temperature': config.get('reservoir_temperature', 25),
            'unit_system': unit_system
        }
        
        # Add optional parameters that GasReservoir actually accepts
        if 'aquifer_influx' in config:
            reservoir_kwargs['aquifer_influx'] = config['aquifer_influx']
        
        reservoir = GasReservoir(**reservoir_kwargs)
        
        return reservoir, production


def create_template_files(output_dir: str = ".", unit_system: UnitSystem = UnitSystem.FIELD):
    """
    Create template input files for users to edit.
    
    Args:
        output_dir: Directory where template files will be created
        unit_system: Unit system for the templates (METRIC or FIELD)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create PVT template CSV
    pvt_file = output_path / "pvt_template.csv"
    with open(pvt_file, 'w', newline='') as f:
        writer = csv.writer(f)
        if unit_system == UnitSystem.FIELD:
            writer.writerow(['pressure', 'Bo', 'Rs', 'Bg', 'Bw', 'cw', 'cf'])
            writer.writerow(['# psia', '# rb/STB', '# SCF/STB', '# rb/SCF', '# rb/STB', '# 1/psi', '# 1/psi'])
            writer.writerow([3330, 1.2511, 510, 0.00087, 1.02, 3e-6, 4e-6])
            writer.writerow([3150, 1.2353, 477, 0.00092, 1.02, 3e-6, 4e-6])
            writer.writerow([3000, 1.2222, 450, 0.00096, 1.02, 3e-6, 4e-6])
        else:
            writer.writerow(['pressure', 'Bo', 'Rs', 'Bg', 'Bw', 'cw', 'cf'])
            writer.writerow(['# kgf/cm2', '# m3/m3', '# m3/m3', '# m3/m3', '# m3/m3', '# 1/kgf/cm2', '# 1/kgf/cm2'])
            writer.writerow([234, 1.25, 91, 0.0049, 1.02, 2.1e-4, 2.8e-4])
            writer.writerow([221, 1.24, 85, 0.0052, 1.02, 2.1e-4, 2.8e-4])
    
    print(f"✓ Created PVT template: {pvt_file}")
    
    # Create production template CSV
    prod_file = output_path / "production_template.csv"
    with open(prod_file, 'w', newline='') as f:
        writer = csv.writer(f)
        if unit_system == UnitSystem.FIELD:
            writer.writerow(['time', 'Np', 'Gp', 'Wp', 'pressure'])
            writer.writerow(['# days', '# STB', '# SCF', '# STB', '# psia'])
            writer.writerow([0, 0, 0, 0, 3330])
            writer.writerow([365, 3295000, 3459750000, 0, 3150])
        else:
            writer.writerow(['time', 'Np', 'Gp', 'Wp', 'pressure'])
            writer.writerow(['# days', '# m3', '# m3', '# m3', '# kgf/cm2'])
            writer.writerow([0, 0, 0, 0, 234])
            writer.writerow([365, 523862, 97969049, 0, 221])
    
    print(f"✓ Created production template: {prod_file}")
    
    # Create config template JSON
    config_file = output_path / "config_template.json"
    config_data = {
        "_comment": "Reservoir configuration file",
        "unit_system": unit_system.name,
        "reservoir_type": "oil",
        "initial_pressure": 3330 if unit_system == UnitSystem.FIELD else 234,
        "reservoir_temperature": 180 if unit_system == UnitSystem.FIELD else 82,
        "initial_water_saturation": 0.2,
        "porosity": 0.18,
        "m": 0.54,
        "aquifer_influx": False,
        "aquifer_constant": 0,
        "_units": {
            "FIELD": {
                "pressure": "psia",
                "temperature": "°F",
                "oil_volume": "STB",
                "gas_volume": "SCF",
                "water_volume": "STB"
            },
            "METRIC": {
                "pressure": "kgf/cm²",
                "temperature": "°C",
                "oil_volume": "m³ std",
                "gas_volume": "m³ std",
                "water_volume": "m³ std"
            }
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"✓ Created config template: {config_file}")
    print(f"\nTemplate files created successfully in: {output_path.absolute()}")
    print("\nYou can edit these files in Excel (for CSV) or any text editor (for JSON).")
