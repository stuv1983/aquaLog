# AquaLog

*A Python & Streamlit–powered local dashboard for tracking water quality, livestock, plants, equipment, dosing, and maintenance across one or more aquariums.*

---

## 📖 Table of Contents

1. [Features](#features)  
2. [Quick Start](#quick-start)  
3. [Configuration](#configuration)  
4. [Folder Structure](#folder-structure)  
5. [Usage Guide](#usage-guide)  
6. [Calculation Details](#calculation-details)  
7. [Database Schema](#database-schema)  
8. [Docker (Optional)](#docker-optional)  
9. [Contributing](#contributing)  
10. [License](#license)

---

## ✨ Features

| Category                  | Highlights                                                                          |
| ------------------------- | ----------------------------------------------------------------------------------- |
| **Offline & Local**       | Runs fully on your machine (Python + SQLite), no cloud or server required.          |
| **Custom Theme & UI**     | Water‐blue palette via `.streamlit/config.toml`; responsive layout; toast alerts.   |
| **Multi-Tank Support**    | Create, select, rename, and delete tank profiles with custom volumes.               |
| **Logging**               | Sidebar form for pH, Temperature, Ammonia, Nitrite, Nitrate, KH, CO₂ + notes.      |
| **Localization & Units**  | Choose language & unit system per user under Settings.                              |
| **Weekly Email Summary**  | User-configurable emails: choose tanks and fields (type, date, notes, cost, stats, cycle).|
| **Overview Dashboard**    | Key metrics, out-of-range banners, rolling sparklines; PDF/Excel export.            |
| **Warnings**              | Real-time alerts & action plans for out-of-range parameters.                        |
| **Data & Analytics**      | Interactive charts, raw data tables, rolling averages, forecasting.                 |
| **Cycle Tracker**         | Nitrogen cycle milestones and progress visualization.                               |
| **Failed Tests**          | Identify and correct incomplete or invalid entries.                                 |
| **Plant & Fish Inventory**| Manage species catalogues, upload CSV, view requirements and thumbnails.            |
| **Maintenance**           | Schedule and record tasks (water changes, filter cleans) under Maintenance tab.     |
| **Equipment**             | Track gear, service intervals, and reminders.                                       |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+  
- pip  
- Git

```bash
# Clone and run
git clone https://github.com/yourusername/aqualog.git
cd aqualog

python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run main.py
```

Open **http://localhost:8501**.

---

## ⚙️ Configuration

| File/Directory                | Purpose                                     |
| ----------------------------- | ------------------------------------------- |
| `.streamlit/config.toml`      | Theme colors, fonts, layout.                |
| `config.py`                   | Safe ranges, defaults, release notes.       |
| `db.py`                       | SQLite helpers, email-settings & custom ranges storage. |
| `requirements.txt`            | Pinned dependencies.                        |
| `aqualog.db`                  | SQLite database (auto-created).             |
| `tank_images/`                | Optional per-tank photo uploads.            |

---

## 📂 Folder Structure

```
aqualog/
├── main.py
├── sidebar.py
├── components.py
├── utils.py
├── db.py
├── config.py
├── requirements.txt
├── tank_images/
├── tabs/
│   ├── analytics_tab.py
│   ├── cycle_tab.py
│   ├── data_analytics_tab.py
│   ├── equipment_tab.py
│   ├── failed_tests_tab.py
│   ├── fertilizer_tab.py
│   ├── fish_inventory_tab.py
│   ├── full_data_tab.py
│   ├── maintenance_tab.py
│   ├── overview_tab.py
│   ├── plant_inventory_tab.py
│   └── warnings_tab.py
└── .streamlit/
    └── config.toml
```

---

## 🛠 Usage Guide

1. **Select & Manage Tanks**  
   - Create new tank profiles with custom volumes under **Settings → Add New Tank**.  
   - Rename or delete tanks under **Settings → Manage Existing Tank**.

2. **Log Water Tests**  
   - Use **🔬 Log Water Test** form in sidebar; click **Save Test**.  
   - Out-of-range triggers toast alerts and in-app banners.

3. **Clear Test Data (Current Tank Only)**  
   - In **Settings → Clear All Water Test Data**, confirm to delete only the selected tank’s records.  

4. **Customize Parameter Ranges**  
   - Under **Settings → Customize Parameter Ranges**, pick a parameter and set your own safe low/high.

5. **Localization & Units**  
   - Under **Settings → Localization & Units**, choose your language and unit system.

6. **Weekly Email Summary**  
   - Configure under **Settings → Weekly Summary Email**: set email, select tanks, and include fields. Email is sent every Monday at 09:00.

7. **Navigate Tabs**  
   - **Overview**: Metrics, charts, exports.  
   - **Warnings**: Live alerts + actions.  
   - **Data & Analytics**: Charts, tables, forecasts.  
   - **Cycle**: Nitrogen-cycle progress.  
   - **Failed Tests**: Review invalid entries.  
   - **Plants / Fish / Equipment**: Inventory & reminders.  
   - **Maintenance**: Task logging; history under expander.

---

## 🧮 Calculation Details

### How Ammonia Toxicity Is Calculated

Total ammonia (NH₃ + NH₄⁺) alone is **misleading**. AquaLog converts it to unionised **NH₃**, the toxic fraction, based on pH & temperature.

> **Formula**  
> `pKa = 0.09018 + 2729.92 / (273.15 + temperature °C)`  
> `NH₃ = total_ammonia / (1 + 10 ** (pKa - pH))`

### KH & GH Conversion from Drops

AquaLog accepts KH and GH as drop counts from liquid test kits. Each drop equates to 1 dKH or 1 dGH, which converts to ppm:

> **Conversion**  
> `ppm = drops × 17.86`

---

## 🗄 Database Schema

```
water_tests
├ id INTEGER PK
├ date TEXT
├ ph REAL
├ temperature REAL
├ ammonia REAL
├ nitrite REAL
├ nitrate REAL
├ kh REAL
├ co2_indicator TEXT
├ notes TEXT
├ tank_id INTEGER → tanks.id

tanks
├ id INTEGER PK
├ name TEXT
├ volume_l REAL
├ start_date TEXT

custom_ranges
├ id INTEGER PK
├ tank_id INTEGER → tanks.id
├ parameter TEXT
├ low REAL
├ high REAL

email_settings
├ user_id INTEGER PK
├ email TEXT
├ tanks TEXT (JSON)
├ include_type BOOLEAN
├ include_date BOOLEAN
├ include_notes BOOLEAN
├ include_cost BOOLEAN
├ include_stats BOOLEAN
├ include_cycle BOOLEAN
```

---

## 🔧 Bug‑Fixes & Behaviour Changes (v3.7)

| ID     | Area                          | Original Problem                                               | Patch / New Behaviour                                              |
| ------ | ----------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| **B‑001** | Nitrate auto‑rounding      | Entering `0 ppm` nitrate displayed as `0.05 ppm` and triggered phantom warning. | Input now rounds down and uses correct safe low at 20 ppm.         |
| **B‑002** | NH₃ toxicity calculation   | Total ammonia flagged lethally without pH/temperature adjustment. | Uses unionised NH₃ fraction; only > 0.05 ppm triggers danger.      |
| **B‑003** | Prime & Stability advice   | Recommended Prime/Stability for ammonia reduction.             | Removed; recommends pure nitrifiers (FritzZyme, SafeStart+).       |
| **B‑004** | pH 6 flagged critical      | pH 6 thrown as error due to KH/GH logic.                       | Expanded safe pH range to 6.0 – 8.0; separate KH/GH logic.         |
| **B‑005** | Legacy imports            | Import from CSV missing helpers causing failures.              | Back‑compat wrappers in `config.py` added.                         |
| **B‑006** | Test‑data deletion scope   | “Clear All” deleted data across all tanks.                     | Scoped deletion to current tank only via updated sidebar logic.    |
| **B‑007** | Localization & Units       | No language/unit selection in UI.                              | Added selection under Settings for locale and units.               |
| **B‑008** | Tank rename persistence   | Renamed tanks were not saved or reflected immediately.         | Fixed rename handler to update DB and refresh sidebar state.       |

---

## 🐳 Docker (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 🤝 Contributing

- Fork → branch → code → PR  
- Format with **black** and lint with **flake8**  
- Update/add tests in `tests/`

---

## 📄 License

**MIT** © 2025 — Stuart Villanti
