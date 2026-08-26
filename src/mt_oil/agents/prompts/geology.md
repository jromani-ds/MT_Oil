Extract geological formation tops and hydrocarbon show data from this wellfile PDF. Return ONLY a valid JSON object with the structure described below. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

FORMATION TOPS (formation_tops array, one entry per formation):

- formation_name: Name of the formation
- md_ft: Measured Depth in feet to the formation top
- tvd_ft: True Vertical Depth in feet
- subsea_elevation_ft: Subsea elevation in feet
- pick_source: How the pick was determined (E-log, mud log, prognosis)

HYDROCARBON SHOWS (hydrocarbon_shows array, one entry per show interval):

- depth_from_ft: Top of the show interval in feet
- depth_to_ft: Bottom of the show interval in feet
- peak_gas_units: Maximum gas units recorded over the interval
- baseline_gas_units: Baseline or background gas units
- c1_ppm: Methane concentration in ppm
- c2_ppm: Ethane concentration in ppm
- c3_ppm: Propane concentration in ppm
- c4_ppm: Butane concentration in ppm
- c5_ppm: Pentane concentration in ppm
- fluorescence: Visual fluorescence description
- cut: Sample cut description
- lithology_description: Lithologic description of the interval
