# MT Oil Analytics Platform

A professional full-stack application for Oil & Gas data analysis, featuring advanced Decline Curve Analysis (DCA), economic modeling (NPV, ROI), and an interactive geospatial dashboard.

## 🏗 Architecture

The project is structured as a modern full-stack application:

-   **Backend**: Python (FastAPI)
    -   **API**: RESTful endpoints for well data, production history, and domain analysis.
    -   **Domain Logic**: Specialized modules for DCA (Arps, Modified Arps, Duong) and Economics (Discounted Cash Flow).
    -   **Data Processing**: High-performance vectorized loading of production data.
-   **Frontend**: TypeScript (React + Vite)
    -   **Map**: Interactive well plotting using `react-leaflet`.
    -   **Dashboard**: Data visualization using `recharts` and `Tailwind CSS`.
    -   **State**: Real-time integration with backend analysis endpoints.

## 🚀 Quick Start

### Prerequisites
-   Python 3.9+
-   Node.js 18+

### 1. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Run Tests to verify system integrity
pytest tests/

# Start the API Server
uvicorn src.mt_oil.api.main:app --reload
```
*API will run at `http://localhost:8000`*

### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Development Server
npm run dev
```
*Dashboard will run at `http://localhost:5173`*

## 📚 Key Features

### Decline Curve Analysis (DCA)
The system automatically fits decline curves to historical production data using optimization techniques (`scipy.optimize`).
-   **Arps**: Standard hyperbolic decline.
-   **Modified Arps**: Hyperbolic with exponential cutoff.
-   **Duong**: Logic for unconventional fractured reservoirs.

### Economic Modeling
Calculates key financial metrics based on DCA forecasts:
-   **NPV**: Net Present Value (discounted cash flow).
-   **ROI**: Return on Investment.
-   **Payout**: Time to recover CAPEX.
-   **Parameters**: Handles price differentials, interacting taxes (Ad Valorem, Severance), and variable operating costs.

## 🛠 Development

### Code Quality
We enforce strict code quality standards:
-   **Formatting**: `black` (Python), `prettier` (coming soon).
-   **Linting**: `ruff` (Python), `eslint` (TypeScript).
-   **Hooks**: `pre-commit` runs these checks automatically.

### Running Tests
```bash
pytest tests/
```

## 🤝 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on branching, commit messages, and PRs.
