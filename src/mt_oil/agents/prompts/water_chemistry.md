Extract produced water chemistry data from this wellfile PDF (from water analysis reports, sundry records, or state water filings). Return ONLY a valid JSON object with the structure described below. If a value is not found, set it to null.

API Number: {api_number}

WATER ANALYSIS (water_chemistry object):

- sample_date: Date the sample was collected
- sample_temp_f: Temperature at measurement in Fahrenheit
- ph: pH of the water sample
- rw_ohm_m: Formation water resistivity in ohm-m (if reported)
- tds_mg_l: Total dissolved solids in mg/L
- na_mg_l: Sodium concentration in mg/L
- ca_mg_l: Calcium concentration in mg/L
- mg_mg_l: Magnesium concentration in mg/L
- ba_mg_l: Barium concentration in mg/L
- sr_mg_l: Strontium concentration in mg/L
- so4_mg_l: Sulfate concentration in mg/L
- cl_mg_l: Chloride concentration in mg/L
- hco3_mg_l: Bicarbonate concentration in mg/L
