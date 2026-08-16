Extract casing, cementing, multi-stage tooling, and cement evaluation data from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

CASING PROGRAM (casing_program array, one entry per string):

- string_type: Type of string (Surface, Intermediate, Production, Liner)
- hole_size_in: Drilled hole size in inches
- casing_od_in: Casing outer diameter in inches
- nominal_weight_lbs_ft: Nominal weight in pounds per foot
- steel_grade: Steel grade designation
- connection_type: Thread or connection type
- setting_depth_ft: Setting depth in feet
- burst_rating_psi: Burst pressure rating
- collapse_rating_psi: Collapse pressure rating

CEMENTING OPERATIONS (cementing_operations array, one entry per job):

- slurry_volume_sacks: Volume of cement in sacks
- slurry_volume_bbls: Volume of cement in barrels
- lead_tail_formulation: Description of lead and tail slurry formulations
- slurry_density_ppg: Slurry density in pounds per gallon
- additives: Cement additives used
- displacement_volume_bbls: Displacement volume in barrels
- bump_pressure_psi: Bump pressure in PSI
- surface_return_volume_bbls: Volume of cement returns at surface in barrels

MULTI-STAGE TOOLS (multi_stage_tools array, one entry per tool):

- stage_tool_depth_ft: Stage/DV tool measured depth
- opening_pressure_psi: Tool opening pressure
- closing_pressure_psi: Tool closing pressure
- isolation_interval_from_ft: Stage isolation interval top
- isolation_interval_to_ft: Stage isolation interval bottom

CEMENT EVALUATION (cement_evaluation object):

- logged_toc_ft: Logged Top of Cement in feet
- verification_method: How the TOC was verified (Cement Bond Log, temperature survey, calculated)
- bond_assessment: Qualitative bond assessment across target pay zones
