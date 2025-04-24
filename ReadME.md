# A Real-Time Web Visualization System for Robot Behavioral Analytics

A lightweight, interactive dashboard that ingests ROS Bridge JSON messages in real time, builds a directed-capability graph, and presents rich analytics—network diagrams, histograms, Sankey flows, centrality scatter plots, heatmaps, and playback controls—all in a single Streamlit app.

---

## 🚀 Features

- **High-throughput ingestion**: 2 000+ events/sec via asyncio or Redis queue
- **Real-time analytics**: sub-500 ms end-to-end latency on 150 × 750 graphs
- **Interactive network**: PyVis diagram with force / hierarchical / circular layouts
- **Playback controls**: ▶ Play, ⏸ Pause, ↺ Reset and draggable timeline
- **Rich charts**: edge-weight histograms, Sankey diagrams, centrality scatter, heatmaps
- **JSON editor**: ACE-based code editor (fallback to textarea) with pretty / minify
- **Filtering**: time-window slider, minimum edge weight, regex search, color-pickers
- **Modular API**: FastAPI endpoints `/events` & `/analytics` with API-key guard
- **Design tokens**: consistent colors, typography, spacing across light & dark themes
- **Automated tests**: pytest suite (92 % coverage), integration checks for API & UI

---

## 📦 Requirements

- Python 3.8+
- Linux, macOS, or Windows
- (Optional) Redis server for high-scale ingestion
- ROS Bridge or JSON logs exported from ROS 1/2

---

## 💾 Installation

```bash
git clone https://github.com/your-org/robot-visualization.git
cd robot-visualization
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate        # Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
# Optional editor enhancement
pip install streamlit-ace
```

---

## ▶️ Running the Application

1. **Ingestion service**
   ```bash
   python ingestion_service.py \
     --rosbridge-url ws://localhost:9090 \
     --queue-type redis \
     --redis-url redis://localhost:6379
   ```
2. **API server**
   ```bash
   uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
   ```
3. **Streamlit front end**
   ```bash
   streamlit run app.py
   ```
4. **Open** http://localhost:8501 and upload a JSON log or point to your live `/events` endpoint.

---

## 🔧 Configuration

Copy `env.template` to `.env` and edit:

```env
API_KEY=your_api_key_here
REDIS_URL=redis://localhost:6379
INGESTION_MODE=asyncio        # or "redis"
PLAYBACK_REFRESH_MS=250
```

---

## 🗂️ Modules Overview

1. **Data-Ingestion Service**

   - Language: Python 3.8+
   - Libs: `rosbridge-client`, `asyncio`, `pydantic`, optional Redis
   - Duties: parse ROS JSON, validate, enqueue with back-pressure, expose Prometheus metrics

2. **Processing & Analytics Engine**

   - Language: Python 3.8+
   - Libs: `NetworkX`, `APScheduler`, `FastAPI`, optional InfluxDB
   - Duties: batch dequeue, update graph, compute centralities & clustering, cache results, snapshot recovery

3. **Visualization Front-End**

   - Framework: Streamlit
   - Libs: `PyVis`, `Altair`, `Plotly`, `streamlit-autorefresh`, `streamlit-ace`
   - Duties: interactive network, analytics tabs, JSON editor, playback UI, theming

4. **Playback & Timeline Controller**

   - Uses `st.session_state` for `playing` & `now`
   - Auto-refresh via `streamlit_autorefresh` every `step` ms
   - Manual scrub through “Current t” slider

5. **API Layer & Security**
   - Endpoints:
     - `GET /events?start=<>&end=<>`
     - `GET /analytics?metrics=degree,betweenness,...`
   - FastAPI with API-Key header guard
   - CORS restricted to front-end origin
   - Rate limiting via `slowapi`

---

## 📊 Performance & KPIs

- **Ingestion throughput**: 5 000 events/sec (target ≥ 2 000)
- **Latency**: 200 ms 90th percentile (target ≤ 500 ms)
- **Frame rate**: 20 fps (target ≥ 15 fps)
- **Graph scale**: 150 nodes × 750 edges (target ≥ 100×500)
- **Test coverage**: 92 % (target ≥ 80 %)

---

## 🎓 Demo

_(Refer to screenshots in `docs/` for uploading JSON, playback, network filters, and analytics.)_

---

## 🤝 Contributing

1. Fork the repo
2. Create branch `feature/your-feature`
3. Commit & push
4. Open a Pull Request—two peer reviews required, all tests must pass

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details

---

**Questions or feedback?** Open an issue or email us at
