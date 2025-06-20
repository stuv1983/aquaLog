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

| :------------------- | :----------------------------------------------------------------------------------------- |

| Offline & Local | Runs entirely on your machine (Python + SQLite); no cloud or external server needed. |

| Custom Theme & UI | Custom theme via `.streamlit/config.toml`, responsive layout, and toast alerts. |

| Multi-Tank Support | Create, select, rename & delete tank profiles with custom volumes. |

| Logging | Sidebar form for pH, Temperature, Ammonia, Nitrite, Nitrate, KH, GH, CO₂, plus notes. |

| Localization & Units | Choose language & unit system per user in Settings. |

| Weekly Email Summary | User-configurable emails: pick tanks & fields to include in a weekly report. |

| Overview Dashboard | Key metrics, out-of-range banners, and parameter trend charts. |

| Warnings | Real-time alerts & action plans for out-of-range parameters and fish compatibility. |

| Data & Analytics | Interactive charts, raw data tables, rolling averages, correlation matrix, and forecasting.|

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

  

Then open `http://localhost:8501` in your browser.

  

## ⚙️ Configuration

  

| File / Directory | Purpose |

| :------------------------------| :-----------------------------------------------------------------|

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

│ └── devcontainer.json # Configuration for VS Code Dev Containers

├── .streamlit/

│ └── config.toml # Streamlit theme and configuration settings

├── main.py # Main application entry point for Streamlit

├── config.py # Global application settings, constants, and action plans

├── components.py # Reusable Streamlit UI components

├── requirements.txt # Python package dependencies for pip

├── README.md # This file

├── run_streamlit.sh # A shell script to run the application (optional)

├── aqualog.db # The SQLite database file

├── fish.csv # Master data for fish species

├── injectFish.py # Script to load fish.csv into the database

├── plants.csv # Master data for plant species

├── injectPlants.py # Script to load plants.csv into the database

├── aqualog_db/ # Package for all database-related code

│ ├── __init__.py # Initializes the database package and exposes repositories

│ ├── schema.py # Defines the authoritative database schema and tables

│ ├── base.py # Base repository class for database connections

│ ├── connection.py # Manages the connection to the SQLite database

│ └── repositories/ # Contains all repository classes for database table operations

│ ├── __init__.py # Exposes all repository classes

│ ├── tank.py # Repository for the `tanks` table

│ ├── water_test.py # Repository for the `water_tests` table

│ ├── custom_range.py # Repository for the `custom_ranges` table

│ ├── email_settings.py # Repository for the `email_settings` table

│ ├── maintenance.py # Repository for maintenance-related tables

│ ├── plant.py # Repository for the master `plants` table

│ ├── owned_plant.py # Repository for the `owned_plants` table

│ ├── fish.py # Repository for the master `fish` table

│ ├── owned_fish.py # Repository for the `owned_fish` table

│ └── equipment.py # Repository for the `equipment` table

├── sidebar/ # Package for all sidebar UI components

│ ├── __init__.py # Initializes the sidebar package

│ ├── sidebar.py # Main entry point for rendering the entire sidebar

│ ├── water_test_form.py # Renders the water test logging form

│ ├── tank_selector.py # Renders the tank selection dropdown

│ ├── settings_panel.py # Renders the settings panel

│ └── release_notes.py # Renders the release notes section

├── tabs/ # Package containing the code for each main UI tab

│ ├── __init__.py # Initializes the tabs package

│ ├── overview_tab.py # Renders the main overview dashboard

│ ├── warnings_tab.py # Renders the warnings and alerts tab

│ ├── data_analytics_tab.py # Renders the data analytics tab

│ ├── cycle_tab.py # Renders the nitrogen cycle tracker

│ ├── plant_inventory_tab.py # Renders the plant inventory tab

│ ├── fish_inventory_tab.py # Renders the fish inventory tab

│ ├── equipment_tab.py # Renders the equipment inventory tab

│ ├── maintenance_tab.py # Renders the maintenance log tab

│ └── tools_tab.py # Renders the tools and calculators tab

└── utils/ # Package for shared utility functions

├── __init__.py # Exposes utility functions for easy import

├── core.py # Core utility functions (caching, mobile detection)

├── chemistry.py # Aquarium chemistry calculation functions

├── validation.py # Data validation and sanitization functions

├── localization.py # Translation and unit conversion functions

└── ui/ # Sub-package for UI-specific helpers

├── __init__.py # Exposes UI helper functions

├── alerts.py # Functions for displaying alerts and toasts

└── charts.py # Functions for creating standardized charts

```

  

## 🛠 Usage Guide

  

<details>

<summary><strong>Select & Manage Tanks</strong></summary>

<p>

Use the "Settings" panel in the sidebar to add, rename, or delete tank profiles. You can also edit a tank’s volume here, which is used in dosing calculations.

</p>

</details>

  

<details>

<summary><strong>Log Water Tests</strong></summary>

<p>

Use the "Log Water Test" form in the sidebar to enter your daily or weekly readings. Out-of-range values will trigger alerts on the "Warnings" tab.

</p>

</details>

  

<details>

<summary><strong>Manage Inventory</strong></summary>

<p>

Use the "Plants" and "Fish" tabs to search the master database and add items to your specific tank’s inventory.

</p>

</details>

  

<details>

<summary><strong>Analyze Data</strong></summary>

<p>

The "Data & Analytics" tab provides powerful tools to visualize your tank’s history, including a raw data table, rolling averages, and a 7-day forecast.

</p>

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

-  **equipment**: Stores information about the user's equipment for each tank.

-  **maintenance_cycles**: Defines recurring maintenance tasks.

-  **maintenance_log**: Records all completed maintenance tasks for each tank.

-  **custom_ranges**: Stores user-defined safe parameter ranges on a per-tank basis.

  

## 🐳 Docker (Optional)

  

To build and run AquaLog in a Docker container:

  

```Dockerfile

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

  

- Format with `black` and lint with `flake8`.

- Add/update tests in `tests/`.

  

## 📄 License

  

MIT © 2025 — Stuart Villanti