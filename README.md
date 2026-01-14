# 🚜 SolidTrack IoT Fleet Management Dashboard

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)
![Status](https://img.shields.io/badge/Status-MVP%20Ready-success)

**SolidTrack** is a comprehensive IoT fleet management dashboard designed for heavy machinery and construction assets. It provides real-time telemetry analysis, dynamic geofencing, and automated alarm management to enhance operational efficiency and safety.

This project demonstrates a full-stack IoT application architecture using Python and Streamlit, simulating real-world scenarios like shock detection, fuel efficiency tracking, and zone violations.

## 🚀 Key Features

### 1. 📊 Operational Dashboard
* **Real-time KPI Tracking:** Instant view of total fleet size, active units, critical alarms, and efficiency scores.
* **Fleet Health:** Summary of connection status, ignition states, and maintenance alerts.

### 2. 🚧 Dynamic Geofence Management
* **Interactive Map:** Create and edit safe zones using a Folium-based interactive map interface.
* **Smart Radius Slider:** Dynamic radius adjustment with real-time visual feedback.
* **Safety Alerts:** Automated warnings for unsafe radius configurations (<500m or >20km).
* **Audit Logs:** Full traceability of site creation and modification events.

### 3. 🔔 Alarm Action Center
* **Live Incident Feed:** Real-time monitoring of critical events (Shock, Low Battery, Speeding, Geofence Breach).
* **Audit Trail:** Professional acknowledgement system recording "Who" handled the alarm and "When".
* **Filtering & Reporting:** Advanced filtering by device/type and one-click export to Excel/CSV.

### 4. 🔍 Telemetry Analysis
* **Deep Dive Analytics:** Historical data visualization for battery usage, engine temperature, and shock events using Plotly.

## 🛠️ Tech Stack

* **Frontend:** Streamlit (Python)
* **Backend:** Python, SQLAlchemy (ORM)
* **Database:** SQLite (Local) / Scalable to PostgreSQL
* **Visualization:** Plotly Express, Folium (Maps)
* **Data Processing:** Pandas

## ⚙️ Installation

1. **Clone the repository**
   ```bash
   git clone [https://github.com/ahmetak86/SolidTrack-IoT-Dashboard.git](https://github.com/ahmetak86/SolidTrack-IoT-Dashboard.git)