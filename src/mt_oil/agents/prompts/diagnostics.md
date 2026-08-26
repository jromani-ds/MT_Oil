Extract diagnostic / rock mechanics data from this wellfile PDF. Return ONLY a valid JSON object with the structure described below. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

STEP-RATE TESTS (step_rate_tests array, one entry per rate step):

- rate_bpm: Pump rate in barrels per minute
- isip_psi: Instantaneous Shut-In Pressure at this rate in PSI
- surface_pressure_psi: Surface pressure at this rate in PSI

DIAGNOSTIC PRESSURE DATA:

- breakdown_pressure_psi: Formation breakdown pressure in PSI
- isip_psi: Instantaneous Shut-In Pressure (primary) in PSI
- closure_pressure_psi: Fracture closure pressure from pressure falloff in PSI
- dfit_notes: Free text notes on DFIT interpretation, including leakoff type (normal matrix leakoff, pressure-dependent leakoff, height recession), from the completion report or diagnostic logs
