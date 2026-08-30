Extract fluid PVT and gas composition data from this wellfile PDF (from gas analysis reports, oil run tickets, or completion filings). Return ONLY a valid JSON object with the structure described below. If a value is not found, set it to null.

API Number: {api_number}

GAS MOLE FRACTIONS (gas_mole_fractions object) — mole fractions as decimals summing to ~1.0:

- c1: Methane mole fraction
- c2: Ethane mole fraction
- c3: Propane mole fraction
- ic4: Iso-butane mole fraction
- nc4: Normal butane mole fraction
- ic5: Iso-pentane mole fraction
- nc5: Normal pentane mole fraction
- c6: Hexanes mole fraction
- c7plus: Heptanes-plus mole fraction
- n2: Nitrogen mole fraction
- co2: Carbon dioxide mole fraction
- h2s: Hydrogen sulfide mole fraction

FLUID PROPERTIES:

- gas_gravity: Gas specific gravity
- btu_scf: Gas heating value in BTU/SCF
- oil_api_gravity: Oil API gravity
- bubble_point_psi: Bubble point (saturation) pressure in PSI
- reservoir_temp_f: Reservoir temperature in Fahrenheit
- water_cut_pct: Water cut as a percentage
