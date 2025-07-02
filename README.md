# AquaLog 🐠📊
A Python & Streamlit–powered local dashboard for tracking water quality, livestock, plants, equipment, dosing & maintenance across one or more aquariums.

## 📖 Table of Contents
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#-configuration)
- [📂 Folder Structure](#-folder-structure)
- [🛠 Usage Guide](#-usage-guide)
- [🧮 Calculation Details](#-calculation-details)
- [🗄 Database Schema](#-database-schema)
- [🐳 Docker (Optional)](#-docker-optional)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## ✨ Features

| Category | Highlights |
| :-- | :-- |
| **Offline & Local** | Runs entirely on your machine (Python + SQLite); no cloud or external server needed. |
| **Custom Theme & UI** | Custom theme via `.streamlit/config.toml`, responsive layout, and toast alerts. |
| **Multi‑Tank Support** | Create, select, rename & delete tank profiles with custom volumes. |
| **Logging** | Sidebar form for pH, Temperature, Ammonia, Nitrite, Nitrate, KH, GH, CO₂, and notes. |
| **Localisation & Units** | Choose language & unit system per user in *Settings*. |
| **Weekly Email Summary** | Pick which tanks & parameters to include in an automatic weekly report. |
| **Overview Dashboard** | Key metrics, out‑of‑range banners, and parameter trend charts. |
| **Warnings** | Real‑time alerts & action plans for out‑of‑range parameters and fish compatibility. |
| **Data & Analytics** | Interactive charts, raw data tables, rolling averages, correlation matrix, forecasting. |
| **Cycle Tracker** | Visualise nitrogen‑cycle milestones & progress for new tanks. |
| **Inventory Management** | Manage catalogues for plants, fish, and equipment per tank. |
| **Maintenance Log** | Schedule & record tasks like water‑changes and filter cleaning. |
| **Tools & Calculators** | Volume, dosing, water‑change, and CO₂ duration calculators. |

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- `pip`

### Installation & Setup
```bash
# Clone the repository
git clone https://github.com/stuv1983/aquaLog
cd aquaLog

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate

# Install required packages
pip install -r requirements.txt

# --- IMPORTANT: INITIAL DATA LOAD ---
# On first run, load the master data for fish & plants
echo "Loading master data..."
python3 injectFish.py
python3 injectPlants.py
# --- END DATA LOAD ---

# Launch the Streamlit app
streamlit run main.py
```

Then open <http://localhost:8501> in your browser.

## ⚙️ Configuration

| File / Directory | Purpose |
| :-- | :-- |
| `.streamlit/config.toml` | Theme colours, fonts & other Streamlit settings. |
| `config.py` | Global constants for safe ranges, default values & action plans. |
| `aqualog_db/` | Database package (schema, repositories, connection logic). |
| `requirements.txt` | Python package requirements. |
| `aqualog.db` | SQLite database file (auto‑created on first run). |
| `fish.csv` / `plants.csv` | Master CSV files used to populate the database. |

## 📂 Folder Structure
```text
aqualog/
├── .devcontainer/           # VS Code Dev Container settings
│   └── devcontainer.json
├── .streamlit/
│   └── config.toml          # Streamlit theme & config
├── main.py                  # App entry‑point
├── config.py                # Global settings & constants
├── components.py            # Re‑usable UI components
├── requirements.txt
├── run_streamlit.sh
├── aqualog.db               # Local SQLite database
├── fish.csv                 # Master data: fish
├── injectFish.py
├── plants.csv               # Master data: plants
├── injectPlants.py
├── aqualog_db/              # Database package
│   ├── __init__.py
│   ├── schema.py
│   ├── base.py
│   ├── connection.py
│   └── repositories/
│       ├── tank.py
│       ├── water_test.py
│       ├── custom_range.py
│       ├── email_settings.py
│       ├── maintenance.py
│       ├── plant.py
│       ├── owned_plant.py
│       ├── fish.py
│       ├── owned_fish.py
│       └── equipment.py
├── sidebar/
│   ├── __init__.py
│   ├── sidebar.py
│   ├── water_test_form.py
│   ├── tank_selector.py
│   ├── settings_panel.py
│   └── release_notes.py
├── tabs/
│   ├── __init__.py
│   ├── overview_tab.py
│   ├── warnings_tab.py
│   ├── data_analytics_tab.py
│   ├── cycle_tab.py
│   ├── plant_inventory_tab.py
│   ├── fish_inventory_tab.py
│   ├── equipment_tab.py
│   ├── maintenance_tab.py
│   └── tools_tab.py
└── utils/
    ├── __init__.py
    ├── core.py
    ├── chemistry.py
    ├── validation.py
    ├── localization.py
    └── ui/
        ├── __init__.py
        ├── alerts.py
        └── charts.py
```

## 🛠 Usage Guide
1. **Select & Manage Tanks** – create, rename or delete tanks via the sidebar.  
2. **Log Water Tests** – enter readings through *Water Test Form*.  
3. **Manage Inventory** – add plants, fish and equipment per tank.  
4. **Analyse Data** – explore dashboards, trends & analytics.  
5. **Use Calculators** – dosing, volume, water‑change & CO₂ tools.

## 🧮 Calculation Details

### Ammonia Toxicity (unionised NH₃)
Total ammonia (NH₃ + NH₄⁺) is converted to the toxic unionised fraction using pH & temperature:

```text
pKa = 0.09018 + 2729.92 / (273.15 + temperature °C)
NH₃  = total_ammonia / (1 + 10 ** (pKa − pH))
```

### KH & GH from Drop Counts
Each drop in common liquid test‑kits equals **1 dKH** or **1 dGH**, which converts to ppm:

```text
ppm = drops × 17.86
```

### Volume Calculation
Calculates volume of a rectangular tank in litres and US gallons from L×W×H.

### Dosing Calculations
Recommended dosages for supplements (e.g. Seachem Alkaline Buffer, Seachem Equilibrium, FritzZyme 7).

### Water‑Change Calculation
Percentage of water to change to reach a target parameter value.

## 🗄 Database Schema
| Table | Purpose |
| :-- | :-- |
| `tanks` | Aquarium details (name, volume). |
| `water_tests` | Time‑series water‑quality readings, linked to a tank. |
| `plants` | Master list of plant species. |
| `owned_plants` | Plants present in a tank & quantity. |
| `fish` | Master list of fish species & requirements. |
| `owned_fish` | Fish present in a tank & quantity. |
| `equipment` | Equipment inventory per tank. |
| `maintenance_cycles` | Recurring maintenance task definitions. |
| `maintenance_log` | Records of completed maintenance. |
| `custom_ranges` | User‑defined safe parameter ranges. |
| `email_settings` | Preferences for weekly summary email. |

## 🐳 Docker (Optional)
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Ensure master data is loaded
RUN python3 injectFish.py && python3 injectPlants.py
EXPOSE 8501
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 🤝 Contributing
1. **Fork** the repo  
2. **Create** a feature branch  
3. **Code** & commit  
4. **Open** a Pull Request

Style: `black`; Lint: `flake8`; Tests live in **`tests/`**.

## 📄 License
**MIT** © 2025 — Stuart Villanti
