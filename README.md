# AquaLog 🐠📊

**A Python & Streamlit–powered local dashboard for tracking water quality, livestock, plants, equipment, dosing & maintenance across one or more aquariums.**

---

## 📖 Table of Contents

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#️-configuration)
- [📂 Folder Structure](#-folder-structure)
- [🛠 Usage Guide](#-usage-guide)
- [🧮 Calculation Details](#-calculation-details)
- [🗄 Database Schema](#-database-schema)
- [🔧 Recent Bug Fixes](#-recent-bug-fixes)
- [🐳 Docker (Optional)](#-docker-optional)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Features

| Category | Highlights |
| :-- | :-- |
| Offline & Local | Runs entirely on your machine (Python + SQLite); no cloud or external server needed. |
| Custom Theme & UI | Ocean‑blue palette via `.streamlit/config.toml`, responsive layout, toast alerts. |
| Multi‑Tank Support | Create, select, rename & delete tank profiles with custom volumes. |
| Logging | Sidebar form for pH, Temperature, Ammonia, Nitrite, Nitrate, KH, CO₂, plus notes. |
| Localization & Units | Choose language & unit system per user in Settings. |
| Weekly Email Summary | User‑configurable emails: pick tanks & fields (type, date, notes, cost, stats, cycle). |
| Overview Dashboard | Key metrics, out‑of‑range banners, rolling sparklines; export to PDF/Excel. |
| Warnings | Real‑time alerts & action plans for out‑of‑range parameters. |
| Data & Analytics | Interactive charts, raw tables, rolling averages, forecasting. |
| Cycle Tracker | Visualise nitrogen‑cycle milestones & progress. |
| Failed Tests | Identify & correct incomplete or invalid entries. |
| Plant & Fish Inventory | Manage species catalogues, upload CSV, view requirements & thumbnails. |
| Maintenance | Schedule & record tasks (water changes, filter cleans) under Maintenance tab. |
| Equipment | Track gear, service intervals & reminders. |

---

## 🚀 Quick Start

### Prerequisites

* Python 3.9+
* `pip`
* `git`
<!-- end list -->

```bash
# Clone & run
git clone https://github.com/yourusername/aqualog.git
cd aqualog

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run main.py
```

Then open **http://localhost:8501** in your browser.

---

## ⚙️ Configuration

| File / Directory | Purpose |
| :-- | :-- |
| `.streamlit/config.toml` | Theme colours, fonts & other Streamlit settings. |
| `config.py` | Global constants for safe ranges, default values & release notes. |
| `aqualog_db/` | Database package (schema, repositories, connection logic). |
| `requirements.txt` | Python package requirements. |
| `aqualog.db` | SQLite database (auto‑created). |
| `tank_images/` | Optional photos for each tank. |

---

## 📂 Folder Structure

*Plaintext*

```plaintext
aqualog/
├── .devcontainer/
│   └── devcontainer.json       # Configuration for VS Code Dev Containers.
│
├── main.py                     # Main application entry-point; launches Streamlit.
├── config.py                   # Central config for safe ranges, action plans, etc.
├── components.py               # Reusable Streamlit UI components and helpers.
├── requirements.txt            # Lists all Python package dependencies.
├── README.md                   # This documentation file.
│
├── aqualog_db/                 # --- DATABASE PACKAGE ---
│   ├── __init__.py             # Initializes the database package.
│   ├── schema.py               # Defines the entire database schema, tables, and indexes.
│   ├── base.py                 # Core `BaseRepository` class for DB connection management.
│   ├── connection.py           # Provides a context-managed database connection.
│   ├── legacy.py               # Backward-compatibility layer for older DB functions.
│   └── repositories/           # Handles all direct table operations (Repositories).
│       ├── __init__.py
│       ├── tank.py             # Repository for the `tanks` table.
│       ├── water_test.py       # Repository for the `water_tests` table.
│       ├── custom_range.py     # Repository for the `custom_ranges` table.
│       └── email_settings.py   # Repository for the `email_settings` table.
│
├── sidebar/                    # --- SIDEBAR UI PACKAGE ---
│   ├── __init__.py             # Initializes the sidebar package.
│   ├── sidebar.py              # Assembles the complete sidebar UI.
│   ├── water_test_form.py      # Renders the form for logging new water tests.
│   ├── tank_selector.py        # Renders the dropdown for selecting the current tank.
│   ├── settings_panel.py       # Renders the collapsible settings panel.
│   └── release_notes.py        # Renders the release notes expander.
│
├── tabs/                       # --- APPLICATION TABS PACKAGE ---
│   ├── overview_tab.py         # Main overview dashboard.
│   ├── warnings_tab.py         # Warnings for out-of-range parameters.
│   ├── data_analytics_tab.py   # Advanced data visualization and analytics.
│   ├── cycle_tab.py            # Tracks the nitrogen cycle progress.
│   ├── failed_tests_tab.py     # History of all tests with out-of-range values.
│   ├── plant_inventory_tab.py  # UI for managing plant inventory.
│   ├── fish_inventory_tab.py   # UI for managing fish inventory.
│   ├── equipment_tab.py        # UI for managing equipment.
│   ├── maintenance_tab.py      # UI for logging maintenance tasks.
│   ├── fertilizer_tab.py       # UI for fertilizer dosing calculations.
│   ├── analytics_tab.py        # (Obsolete) Older version of the analytics tab.
│   ├── full_data_tab.py        # (Obsolete) Older data view tab.
│   └── sidebar_entry.py        # (Obsolete) Older version of the sidebar logic.
│
├── utils/                      # --- UTILITY FUNCTIONS PACKAGE ---
│   ├── __init__.py             # Initializes the utils package.
│   ├── core.py                 # Core utility functions (e.g., caching).
│   ├── chemistry.py            # Contains all scientific calculation functions.
│   ├── validation.py           # Functions for validating user input and dataframes.
│   ├── localization.py         # Handles translation and unit conversion.
│   ├── database.py             # (Obsolete) Older database helper functions.
│   └── ui/                     # UI-specific utilities.
│       ├── __init__.py
│       ├── alerts.py           # Functions for displaying alerts and toasts.
│       └── charts.py           # Functions for creating Altair charts.
│
└── .streamlit/
    └── config.toml             # Streamlit theme configuration.
```

---

## 🛠 Usage Guide

<details>
<summary><strong>Select & Manage Tanks</strong></summary>

Settings → Add New Tank – create tank profiles with custom volumes.  
Settings → Manage Existing Tank – rename or delete tanks.
</details>

<details>
<summary><strong>Log Water Tests</strong></summary>

Use 🔬 Log Water Test form in the sidebar ⇒ Save Test.  
Out‑of‑range values trigger toast alerts & in‑app banners.
</details>

<details>
<summary><strong>Clear Test Data (current tank only)</strong></summary>

Settings → Clear All Water Test Data – confirm to delete the selected tank’s records only.
</details>

<details>
<summary><strong>Customise Parameter Ranges</strong></summary>

Settings → Customize Parameter Ranges – pick a parameter & set custom safe low/high values.
</details>

<details>
<summary><strong>Localization & Units</strong></summary>

Settings → Localization & Units – choose language & unit system.
</details>

<details>
<summary><strong>Weekly Email Summary</strong></summary>

Settings → Weekly Summary Email – set email, choose tanks & fields.  
Summary is sent every Monday at 09:00.
</details>

Use the main tabs to explore Overview metrics, detailed analytics, inventory, and maintenance logs.

---

## 🧮 Calculation Details


### Ammonia Toxicity (unionised NH₃)

Total ammonia (NH₃ + NH₄⁺) alone is misleading. AquaLog converts it to the toxic unionised NH₃ fraction using pH & temperature:

*Plaintext*

```plaintext
pKa = 0.09018 + 2729.92 / (273.15 + temperature °C)
NH₃  = total_ammonia / (1 + 10 ** (pKa − pH))
```

---

#### How it works

1. **Calculate pKa**  
   The pKa is the acid dissociation constant for the equilibrium  
   NH₄⁺ ⇌ NH₃ + H⁺.  
   It shifts with temperature so that at higher temperatures more ammonia exists as NH₃.

2. **Apply Henderson–Hasselbalch**  
   The ratio  
   ```
   [NH₄⁺] / [NH₃] = 10^(pKa - pH)
   ```  
   is rearranged to isolate the unionised fraction:
   ```
   [NH₃] = total_ammonia / (1 + 10^(pKa - pH))
   ```

---

#### Why this matters

- **pH dependence**  
  - When **pH < pKa**, most ammonia is in the **NH₄⁺** (ionised) form—much less toxic.  
  - When **pH > pKa**, the fraction of **NH₃** (unionised) increases dramatically.

- **Temperature dependence**  
  - **Warmer water** lowers pKa (denominator shrinks), shifting more total ammonia into the NH₃ form.  
  - **Colder water** raises pKa, keeping more ammonia as the safer NH₄⁺ form.

By reporting the actual NH₃ concentration rather than raw total ammonia, AquaLog lets you accurately assess toxicity risk and take timely corrective action (e.g., water changes, pH buffering, biofilter optimization).


### KH & GH from Drop Counts

Each drop in common liquid test‑kits equals 1 dKH or 1 dGH, which converts to ppm:

*Plaintext*

```plaintext
ppm = drops × 17.86
```

---

## 🗄 Database Schema

*Plaintext*

```plaintext
tanks
 ├ id INTEGER PK
 ├ name TEXT
 ├ volume_l REAL
 └ start_date TEXT

water_tests
 ├ id INTEGER PK
 ├ date TEXT
 ├ ph, ammonia, nitrite, nitrate, temperature, kh, gh REAL
 ├ co2_indicator TEXT
 ├ notes TEXT
 └ tank_id INTEGER → tanks.id

plants
 ├ plant_id INTEGER PK
 ├ plant_name TEXT
 └ thumbnail_url TEXT

owned_plants
 ├ plant_id INTEGER → plants.plant_id
 ├ tank_id INTEGER → tanks.id
 └ PRIMARY KEY(plant_id, tank_id)

fish
 ├ fish_id INTEGER PK
 ├ species_name TEXT
 ├ common_name TEXT
 └ image_url TEXT

owned_fish
 ├ id INTEGER PK
 ├ fish_id INTEGER → fish.fish_id
 ├ tank_id INTEGER → tanks.id
 └ quantity INTEGER

custom_ranges
 ├ id INTEGER PK
 ├ tank_id INTEGER → tanks.id
 ├ parameter TEXT
 ├ low REAL
 └ high REAL
```

---

## 🔧 Recent Bug Fixes (v3.8)

| ID | Area | Original Problem | Patch / New Behaviour |
| :-- | :-- | :-- | :-- |
| B‑009 | Database Startup | Crash with disk I/O error in some environments. | Disabled WAL mode for broader compatibility – startup crash resolved. |
| B‑010 | Fish Inventory | “no such column: species_name” on Fish tab. | Aligned `schema.py` with app code – fish table always has species_name. |
| B‑011 | Fish Inventory | Error viewing owned fish due to missing quantity. | Added quantity column to owned_fish schema. |
| B‑012 | Unique Constraint | owned_plants allowed duplicates for same plant/tank. | Rebuilt with composite PK (plant_id, tank_id) to prevent duplicates. |

---

## 🐳 Docker (Optional)

```Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 🤝 Contributing

Fork → create feature branch → code → open PR.  
Format with **black** and lint with **flake8**.  
Add/ update tests in **`tests/`**.

---

## 📄 License

MIT © 2025 — Stuart Villanti
