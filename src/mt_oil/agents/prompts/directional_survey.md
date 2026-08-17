Extract the directional MWD survey table from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

IMPORTANT — EXTRACT EVERY SURVEY STATION. Do NOT truncate or summarize the survey table. Include the complete list of all survey points (MD, Inclination, Azimuth, TVD) from surface to TD. The survey table may be long — capture all rows.

SURVEY POINTS (survey_points array, one entry per station, ALL stations):

- md_ft: Measured depth in feet
- inclination_deg: Inclination in degrees
- azimuth_deg: Azimuth in degrees
- tvd_ft: True vertical depth in feet (if reported)
- dls_deg_per_100ft: Dogleg severity in degrees per 100 ft (if reported)

SUMMARY:

- max_dls_deg_per_100ft: Maximum DLS across the entire well
- lateral_max_dls_deg_per_100ft: Maximum DLS within the horizontal lateral section
