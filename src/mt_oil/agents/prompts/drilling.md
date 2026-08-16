Extract drilling fluid parameters, bit performance data, and wellbore event records from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

DRILLING FLUID PARAMETERS (drilling_fluid_params array, one entry per depth interval):

- depth_ft: Depth of the fluid measurement in feet
- mud_type: Mud system type (water-based, oil-based invert, etc.)
- mud_weight_ppg: Mud weight in pounds per gallon
- funnel_viscosity_sec: Funnel viscosity in seconds
- fluid_loss_cc: Fluid loss or water loss in cc
- chlorides_ppm: Chloride concentration in ppm
- oil_water_ratio: Oil-to-water ratio

BIT RUNS (bit_runs array, one entry per bit run):

- bit_number: Sequential bit number
- bit_size_in: Bit diameter in inches
- manufacturer: Bit manufacturer name
- iadc_code: IADC bit code or cutter type description
- cutter_type: Cutter type (PDC, roller cone, etc.)
- depth_in_ft: Depth the bit went in (start depth)
- depth_out_ft: Depth the bit came out (end depth)
- rotating_hours: Total rotating hours on the bit
- footage_drilled_ft: Total footage drilled by the bit
- avg_rop_ft_per_hr: Average rate of penetration in feet per hour

WELLBORE EVENTS (wellbore_events array, one entry per event):

- event_type: Type of event (lost circulation, gas kick, tight hole, etc.)
- depth_ft: Depth where the event occurred
- description: Detailed description of the event
- treatment_type: Treatment or remediation applied
