"""
Example: Reading Input Data from Files

This example demonstrates how to use external input files (CSV and JSON)
to provide data to the material balance calculations.

Users can prepare their data in Excel or any text editor and save as CSV/JSON.
The application will read these files and perform the analysis.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from material_balance import InputReader, create_template_files, UnitSystem
from material_balance.utils import print_results_summary, save_results_to_csv, save_production_analysis_to_csv


def example_read_from_files():
    """
    Example: Read reservoir data from external files
    """
    print("\n" + "="*70)
    print("EXAMPLE: READING DATA FROM EXTERNAL FILES")
    print("="*70 + "\n")
    
    # Define file paths
    input_dir = os.path.join(os.path.dirname(__file__), 'input_data')
    pvt_file = os.path.join(input_dir, 'dake_pvt.csv')
    production_file = os.path.join(input_dir, 'dake_production.csv')
    config_file = os.path.join(input_dir, 'dake_config.json')
    
    print(f"Reading input files from: {input_dir}\n")
    print(f"  - PVT properties: dake_pvt.csv")
    print(f"  - Production data: dake_production.csv")
    print(f"  - Configuration: dake_config.json\n")
    
    # Create reservoir and production data from files
    try:
        reservoir, production = InputReader.create_oil_reservoir_from_files(
            pvt_file=pvt_file,
            production_file=production_file,
            config_file=config_file
        )
        
        print("✓ Successfully loaded all input data\n")
        
        # Display reservoir configuration
        print("Reservoir Configuration:")
        print(f"  - Initial pressure: {reservoir.Pi:.2f} kgf/cm² (converted from input)")
        print(f"  - Temperature: {reservoir.T:.2f} K (converted from input)")
        print(f"  - Gas cap ratio (m): {reservoir.m}")
        print(f"  - Production data points: {len(production.pressure)}\n")
        
        # Calculate STOIIP
        print("Calculating STOIIP from production history...\n")
        stoiip_values, stats = reservoir.calculate_STOIIP_from_production_data(production)
        
        # Save results
        save_production_analysis_to_csv(
            production,
            stoiip_values,
            'production_analysis_from_files.csv',
            reservoir
        )
        
        # Print summary
        print("\n" + "="*70)
        print("RESULTS SUMMARY")
        print("="*70 + "\n")
        
        print(f"Mean STOIIP:   {stats['mean']/1e6:.2f} Mm³ std")
        print(f"Median STOIIP: {stats['median']/1e6:.2f} Mm³ std")
        print(f"Std Dev:       {stats['std']/1e6:.2f} Mm³ std")
        print(f"Min:           {stats['min']/1e6:.2f} Mm³ std")
        print(f"Max:           {stats['max']/1e6:.2f} Mm³ std")
        print(f"CV:            {stats['coefficient_of_variation']:.4f}")
        print(f"Valid points:  {stats['count']} of {len(production.pressure)}")
        
        # Convert results to field units for display
        from material_balance import UnitConverter
        converter = UnitConverter()
        
        mean_stoiip_field = converter.oil_volume_from_metric(
            stats['mean'],
            to_system=UnitSystem.FIELD
        )
        
        print("\n" + "="*70)
        print("RESULTS IN FIELD UNITS")
        print("="*70)
        print(f"\nMean STOIIP: {mean_stoiip_field:,.0f} STB")
        print(f"            ({mean_stoiip_field/1e6:.2f} MMSTB)")
        
        if production.Np is not None and len(production.Np) > 0:
            # Convert cumulative production back to field units
            cum_prod_field = converter.oil_volume_from_metric(
                production.Np[-1],
                to_system=UnitSystem.FIELD
            )
            recovery_factor = (cum_prod_field / mean_stoiip_field) * 100
            print(f"\nCurrent Recovery Factor: {recovery_factor:.2f}%")
            print(f"Cumulative Oil Production: {cum_prod_field:,.0f} STB")
            print(f"Remaining Oil: {mean_stoiip_field - cum_prod_field:,.0f} STB")
        
        print("\n" + "="*70)
        print("Example completed successfully!")
        print("="*70 + "\n")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nInput files not found. Would you like to create template files?")
        print("Run the create_templates example to generate template files.\n")
        return
    except Exception as e:
        print(f"❌ Error processing input files: {e}")
        import traceback
        traceback.print_exc()
        return


def example_create_templates():
    """
    Example: Create template input files for users to edit
    """
    print("\n" + "="*70)
    print("CREATING TEMPLATE INPUT FILES")
    print("="*70 + "\n")
    
    output_dir = os.path.join(os.path.dirname(__file__), 'input_templates')
    
    print(f"Creating template files in: {output_dir}\n")
    
    from material_balance import UnitSystem
    
    # Create templates in both unit systems
    print("Creating FIELD units templates:")
    create_template_files(
        output_dir=os.path.join(output_dir, 'field_units'),
        unit_system=UnitSystem.FIELD
    )
    
    print("\nCreating METRIC units templates:")
    create_template_files(
        output_dir=os.path.join(output_dir, 'metric_units'),
        unit_system=UnitSystem.METRIC
    )
    
    print("\n" + "="*70)
    print("INSTRUCTIONS FOR USING TEMPLATE FILES")
    print("="*70)
    print("""
1. Navigate to the 'input_templates' folder
2. Choose either 'field_units' or 'metric_units' subfolder
3. Open the CSV files in Excel or any spreadsheet software
4. Edit the data according to your reservoir parameters
5. Save the files (keep the CSV format)
6. Edit the JSON config file with a text editor
7. Run your analysis using the InputReader class

Template files included:
  - pvt_template.csv: PVT properties (pressure, Bo, Rs, Bg, etc.)
  - production_template.csv: Production history (time, Np, Gp, Wp, pressure)
  - config_template.json: Reservoir configuration (temperature, m, porosity, etc.)

Note: CSV files can be edited in Excel and saved as CSV (Comma delimited)
      JSON files should be edited in a text editor (Notepad, VS Code, etc.)
""")


if __name__ == "__main__":
    # First, try to read from files
    example_read_from_files()
    
    # Optionally, create templates if files don't exist
    # Uncomment the line below to create template files
    # example_create_templates()
