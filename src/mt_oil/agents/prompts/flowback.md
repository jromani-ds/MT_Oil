Extract flowback and load recovery data from this wellfile PDF (from swab / flowback logs and service company workover tickets). Return ONLY a valid JSON object with the structure described below. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

SWAB / FLOWBACK TALLY (swab_tally array, one entry per hourly reading):

- hour: Elapsed hour since start of flowback
- fluid_recovered_bbls: Cumulative fluid recovered in barrels
- choke_inches: Choke size in inches at this hour
- flowing_pressure_psi: Surface flowing pressure in PSI

LOAD RECOVERY:

- cumulative_load_recovered_bbls: Total frac load fluid returned before stabilization, in barrels

PROPPANT FLOWBACK (proppant_flowback array, one entry per solids event):

- volume_bbls: Volume of proppant/sand returned in barrels
- mesh_size: Mesh size of the returned proppant
- description: Description of the event

FLOWBACK NOTES:

- flowback_notes: Free text narrative of the flowback period
