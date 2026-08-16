Extract the following completion, stimulation, and downhole tubular parameters from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found or illegible, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

GENERAL WELL DATA:

- well_name: Official well name and number
- tvd_ft: True Vertical Depth in feet
- md_ft: Total Measured Depth in feet
- lateral_length_ft: Horizontal lateral length in feet
- total_clean_fluid_bbls: Total clean fracturing fluid in barrels
- total_proppant_lbs: Total proppant/sand weight in pounds
- max_treating_pressure_psi: Maximum treating pressure in PSI
- casing_intermediate_depth_ft: Intermediate casing setting depth in feet

IP / FLOW TEST (ip_flow_test object):

- test_duration_hrs: Duration of the test in hours
- oil_rate_24hr_bbls: 24-hour equivalent oil rate in barrels
- gas_rate_24hr_mcf: 24-hour equivalent gas rate in MCF
- water_rate_24hr_bbls: 24-hour equivalent water rate in barrels
- choke_size_inches: Choke size in inches
- flowing_tubing_pressure_psi: Flowing tubing pressure in PSI
- shut_in_tubing_pressure_psi: Shut-in tubing pressure in PSI
- test_method: How the test was conducted (swab test, flowing, etc.)

PERFORATIONS (perforations array, one entry per interval):

- top_md_ft: Top measured depth of perforated interval
- bottom_md_ft: Bottom measured depth of perforated interval
- shots_per_ft: Shots per foot
- gun_charge_diameter_in: Gun or charge diameter in inches
- gun_type: Gun or charge type description
- phase_angle_deg: Phase angle in degrees
- formation_name: Name of the formation perforated
- status: Whether open, squeezed, or isolated

STIMULATION STAGES (stimulation_stages array, one entry per stage):

- treatment_type: Type of treatment (acid breakdown, matrix acid, hydraulic fracture, etc.)
- stage_number: Sequential stage number
- fluid_volume_bbls: Fluid volume pumped in barrels
- chemical_additives: Chemical additives and their concentrations
- diverter_specs: Diverter or ball sealer specifications
- max_treating_pressure_psi: Maximum treating pressure
- avg_treating_pressure_psi: Average treating pressure
- injection_rate_bpm: Injection rate in barrels per minute
- isip_psi: Instantaneous Shut-In Pressure

DOWNHOLE TUBULARS (downhole_tubulars object):

- tubing_od_in: Tubing outer diameter in inches
- tubing_weight_lbs_ft: Tubing weight in pounds per foot
- tubing_grade: Steel grade of the tubing
- thread_type: Thread / connection type
- eot_depth_ft: End of Tubing measured depth
- seating_nipple_depth_ft: Seating Nipple measured depth
- tubing_anchor_catcher_depth_ft: Tubing Anchor Catcher measured depth
- applied_pretension_lbs: Applied pretension load in pounds
