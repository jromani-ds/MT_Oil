# Issue #59 — Add Wellfile Download Links

## Overview

Provide a direct download link for official wellfiles inside the "Well Economics" card UI.
**Primary:** Montana MBOGC Image Server (`bogapps.dnrc.mt.gov`)
**Fallback:** Public GCS direct link (data bucket already has `allUsers` objectViewer IAM)

## Steps

### 1. Backend: config.py

- Add `wellfile_state_url_template` setting from `WELLFILE_STATE_URL_TEMPLATE` env var
- Default: `"https://bogapps.dnrc.mt.gov/html/imaging.aspx?num={api_number}"`

### 2. Backend: main.py

- Add `GET /wells/{api_number}/wellfile` endpoint (after `get_well_details`, line ~248)
- Formats API number (strip hyphens/whitespace, first 10 chars)
- Returns `{"primary_url": state_url, "fallback_url": gcs_url}`
- GCS URL: `https://storage.googleapis.com/{bucket}/wells/pdfs/{api}/{api[:10]}.pdf`

### 3. Backend: tests/test_api.py

- `test_wellfile_url` — validates URL formatting
- `test_wellfile_url_unknown_well` — validates 404

### 4. Frontend: client.ts

- `WellfileResponse` interface: `{ primary_url: string; fallback_url: string }`
- `getWellfileUrl(apiNumber: string)` function

### 5. Frontend: Dashboard.tsx (Economics card)

- "Download Official Wellfile" button in card header
- Styled like existing "Recalculate" button
- Opens `primary_url` in new tab

### 6. Git

- Branch: `feature/wellfile-download` off `dev`
- Commit, push, PR to `dev` referencing `#59`
