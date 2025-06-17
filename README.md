# AquaLog 🐠📊

A Python & Streamlit–powered local dashboard for tracking water quality, livestock, plants, equipment, dosing & maintenance across one or more aquariums.

  

## 📖 Table of Contents

- [✨ Features](#-features)

- [🚀 Quick Start](#-quick-start)

- [⚙️ Configuration](#️-configuration)

- [📂 Folder Structure](#-folder-structure)

- [🛠 Usage Guide](#-usage-guide)

- [🧮 Calculation Details](#-calculation-details)

- [🗄 Database Schema](#-database-schema)

- [🐳 Docker (Optional)](#-docker-optional)

- [🤝 Contributing](#-contributing)

- [📄 License](#-license)

  

## ✨ Features

| Category | Highlights |

| :-------------------- | :------------------------------------------------------------------------------------------ |

| Offline & Local | Runs entirely on your machine (Python + SQLite); no cloud or external server needed. |

| Custom Theme & UI | Custom theme via `.streamlit/config.toml`, responsive layout, and toast alerts. |

| Multi-Tank Support | Create, select, rename & delete tank profiles with custom volumes. |

| Logging | Sidebar form for pH, Temperature, Ammonia, Nitrite, Nitrate, KH, GH, CO₂, plus notes. |

| Localization & Units | Choose language & unit system per user in Settings. |

| Weekly Email Summary | User-configurable emails: pick tanks & fields to include in a weekly report. |

| Overview Dashboard | Key metrics, out-of-range banners, and parameter trend charts. |

| Warnings | Real-time alerts & action plans for out-of-range parameters and fish compatibility. |

| Data & Analytics | Interactive charts, raw data tables, rolling averages, correlation matrix, and forecasting. |

| Cycle Tracker | Visualise nitrogen-cycle milestones & progress for new tanks. |

| Inventory Management | Manage catalogues for plants, fish, and equipment per tank. |

| Maintenance Log | Schedule & record tasks like water changes and filter cleaning. |

  

## 🚀 Quick Start

  

### Prerequisites

- Python 3.9+

- pip

  

### Installation & Setup

  

```bash

# Clone the repository

git  clone <your-repo-url>

cd  aquaLog

  

# Create and activate a virtual environment

python3  -m  venv  .venv

source  .venv/bin/activate

# On Windows, use: .venv\Scripts\activate

  

# Install required packages

pip  install  -r  requirements.txt

  

# --- IMPORTANT: INITIAL DATA LOAD ---

# On first setup, you must load the master data for fish and plants.

echo  "Loading master data..."

python3  injectFish.py

python3  injectPlants.py

# --- END DATA LOAD ---

  

# Run the Streamlit application

streamlit  run  main.py

```

  

Then open [http://localhost:8501](http://localhost:8501) in your browser.

  

## ⚙️ Configuration

| File / Directory | Purpose |

| :-------------------------- | :----------------------------------------------------------------------- |

| `.streamlit/config.toml` | Theme colours, fonts & other Streamlit settings. |

| `config.py` | Global constants for safe ranges, default values & action plans. |

| `aqualog_db/` | Database package (schema, repositories, connection logic). |

| `requirements.txt` | Python package requirements. |

| `aqualog.db` | The SQLite database file (auto-created on first run). |

| `fish.csv` / `plants.csv` | Master CSV files used to populate the database. |

  

## 📂 Folder Structure

  

This represents the clean and final structure of the project.

  

```plaintext

aqualog/

├── .devcontainer/

│ └── devcontainer.json

├── .streamlit/

│ └── config.toml

│

├── main.py

├── config.py

├── components.py

├── requirements.txt

├── README.md

├── run_streamlit.sh

│

├── aqualog.db

├── fish.csv

├── injectFish.py

├── plants.csv

├── injectPlants.py

│

├── aqualog_db/

│ ├── __init__.py

│ ├── schema.py

│ ├── base.py

│ ├── connection.py

│ └── repositories/

│ ├── __init__.py

│ ├── tank.py

│ ├── water_test.py

│ ├── custom_range.py

│ └── email_settings.py

│

├── sidebar/

│ ├── __init__.py

│ ├── sidebar.py

│ ├── water_test_form.py

│ ├── tank_selector.py

│ ├── settings_panel.py

│ └── release_notes.py

│

├── tabs/

│ ├── __init__.py

│ ├── overview_tab.py

│ ├── warnings_tab.py

│ ├── data_analytics_tab.py

│ ├── cycle_tab.py

│ ├── failed_tests_tab.py

│ ├── plant_inventory_tab.py

│ ├── fish_inventory_tab.py

│ ├── equipment_tab.py

│ └── maintenance_tab.py

│

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

  

## 🛠 Usage Guide

  

<details>

<summary><strong>Select & Manage Tanks</strong></summary>

  

Use the "Settings" panel in the sidebar to add, rename, or delete tank profiles. You can also edit a tank’s volume here, which is used in dosing calculations.

  

</details>

  

<details>

<summary><strong>Log Water Tests</strong></summary>

  

Use the "Log Water Test" form in the sidebar to enter your daily or weekly readings. Out-of-range values will trigger alerts on the "Warnings" tab.

  

</details>

  

<details>

<summary><strong>Manage Inventory</strong></summary>

  

Use the "Plants" and "Fish" tabs to search the master database and add items to your specific tank’s inventory.

  

</details>

  

<details>

<summary><strong>Analyze Data</strong></summary>

  

The "Data & Analytics" tab provides powerful tools to visualize your tank’s history, including a raw data table, rolling averages, and a 7-day forecast.

  

</details>

  

## 🧮 Calculation Details

  

### Ammonia Toxicity (unionised NH₃)

Total ammonia (NH₃ + NH₄⁺) alone is misleading. AquaLog converts it to the toxic unionised NH₃ fraction using pH & temperature:

  

```plaintext

pKa = 0.09018 + 2729.92 / (273.15 + temperature °C)

NH₃ = total_ammonia / (1 + 10 ** (pKa − pH))

```

  

### KH & GH from Drop Counts

Each drop in common liquid test-kits equals 1 dKH or 1 dGH, which converts to ppm:

  

```plaintext

ppm = drops × 17.86

```

  

## 🗄 Database Schema

  

A high-level overview of the main database tables and their relationships:

  

-  **tanks**: Stores information about each aquarium (name, volume).

-  **water_tests**: Stores all time-series water quality readings, linked to a tank.

-  **plants**: The master list of all possible plant species.

-  **owned_plants**: Links plants from the master list to a specific tank.

-  **fish**: The master list of all possible fish species and their requirements.

-  **owned_fish**: Links fish from the master list to a specific tank and stores the quantity.

-  **custom_ranges**: Stores user-defined safe parameter ranges on a per-tank basis.

-  **maintenance_log**: Records all completed maintenance tasks for each tank.

  

## 🐳 Docker (Optional)

  

To build and run AquaLog in a Docker container:

  

```dockerfile

# Dockerfile

FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Ensure data is loaded during build or via an entrypoint script

RUN python3 injectFish.py && python3 injectPlants.py

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

```

  

## 🤝 Contributing

  

Fork → create feature branch → code → open PR.

Format with black and lint with flake8.

Add/update tests in `tests/`.

  

## 📄 License

  

MIT © 2025 — Stuart Villanti