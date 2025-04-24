
from __future__ import annotations
import json, re, datetime
import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
from streamlit.components.v1 import html
from streamlit_autorefresh import st_autorefresh
import altair as alt
import plotly.graph_objs as go   # pie & scatter

# Optional ACE
try:
    from streamlit_ace import st_ace
    USE_ACE = True
except ModuleNotFoundError:
    USE_ACE = False

ACCENT = "#ff4b4b"
NET_HEIGHT = 700  # px

# ─── Helpers ────────────────────────────────────────────────────
def parse_events(raw: list[dict]) -> pd.DataFrame:
    rows = []
    for it in raw:
        if it.get("topic") != "/capabilities/events": continue
        m = it["msg"]; s = m["header"]["stamp"]
        ts = s["secs"] + s["nsecs"] * 1e-9
        src = m["source"]["capability"].strip()
        tgt = m["target"]["capability"].strip() or src
        txt = (m["target"]["text"] or "event").strip()
        typ = txt.split(":")[0][:60]
        if src:
            rows.append(dict(timestamp=ts, source=src,
                             target=tgt, type=typ, text=txt))
    if not rows: return pd.DataFrame()
    df = (pd.DataFrame(rows)
          .sort_values("timestamp")
          .reset_index(drop=True))
    df["timestamp"] -= df["timestamp"].iloc[0]
    return df

def build_graph(df: pd.DataFrame, min_w: int):
    agg = df.groupby(["source","target"]).size().reset_index(name="w")
    agg = agg[agg.w >= min_w]
    G = nx.DiGraph()
    for _, r in agg.iterrows():
        G.add_edge(r.source, r.target, weight=int(r.w))
    for n in set(agg.source) | set(agg.target):
        G.add_node(n)
    return G, agg

def centralities(G: nx.DiGraph):
    if not G.nodes: return {}, {}, {}
    deg = nx.degree_centrality(G)
    btw = nx.betweenness_centrality(G)
    try:
        eig = nx.eigenvector_centrality_numpy(G)
    except Exception:
        eig = {n: 0 for n in G.nodes()}
    return deg, btw, eig

def safe_regex(df: pd.DataFrame, pat: str):
    if not pat: return df
    try:
        rx = re.compile(pat, re.I)
        mask = df.source.str.contains(rx) | df.target.str.contains(rx)
    except re.error:
        mask = df.source.str.contains(pat, case=False) | \
               df.target.str.contains(pat, case=False)
    return df[mask]

cut = lambda s,n: (s[:n]+"…") if n and len(s)>n>0 else s

# ─── UI skeleton ────────────────────────────────────────────────
st.set_page_config("🤖 Capability Event Dashboard", layout="wide")

with st.sidebar:
    st.markdown("## 📂 Upload")
    up = st.file_uploader("JSON", type=["json"])
    raw_text = up.read().decode() if up else "[]"

intro, edit, dash, insp, table, stat = st.tabs(
    ["ℹ️ Overview", "📝 Editor", "📊 Dashboard", "🔍 Inspector", "📑 Data", "📈 Analytics"]
)

with intro:
    st.markdown(
        f"<h2 style='text-align:center;color:{ACCENT}'>Capability Event Dashboard</h2>",
        unsafe_allow_html=True)
    st.write("Upload / edit a JSON log of `/capabilities/events` and explore the system’s information flow.")

# Editor tab
with edit:
    if USE_ACE:
        content = st_ace(raw_text, language="json", wrap=True,
                         theme="monokai", height="480px")
    else:
        content = st.text_area("JSON", raw_text, height=480)

    a,b,c = st.columns(3)
    if a.button("Pretty"):
        try: content = json.dumps(json.loads(content), indent=2); st.experimental_rerun()
        except: st.warning("Bad JSON")
    if b.button("Minify"):
        try: content = json.dumps(json.loads(content), separators=(",",":")); st.experimental_rerun()
        except: st.warning("Bad JSON")
    c.download_button("Save", content.encode(), "events.json", "application/json")
    if st.button("Apply"): raw_text = content; st.experimental_rerun()

# Parse JSON
try:
    raw = json.loads(raw_text)
    df_all = parse_events(raw)
except Exception as e:
    dash.error(e); st.stop()

if df_all.empty:
    dash.warning("No events in JSON."); st.stop()

# Sidebar: filters & style
with st.sidebar:
    st.markdown("## 🔎 Filters")
    types_all = sorted(df_all.type.unique())
    sel_types = st.multiselect("Event text", types_all, types_all)
    t_min, t_max = df_all.timestamp.min(), df_all.timestamp.max()
    window = st.slider("Time window (s)", 0.0, float(t_max),
                       (0.0, float(t_max)), 0.1)
    regex = st.text_input("Capability regex")
    ecount = df_all.groupby(["source","target"]).size().reset_index(name="w")
    min_w = st.slider("Min edge weight", 1, int(ecount.w.max()), 1)

    st.markdown("## 🎨 Style")
    theme  = st.selectbox("Theme", ["light","dark"])
    layout = st.selectbox("Layout", ["force","hierarchical","circular"])
    physics= st.checkbox("Physics", layout=="force")
    if physics:
        spring = st.slider("Spring length",50,500,200)
        repel  = st.slider("Repulsion",0,5000,1200)
    arrows = st.checkbox("Arrows",True)
    lablen = st.slider("Label length",0,40,20)

    st.markdown("### Palette")
    palette = {t: st.color_picker(t, f"#{hash(t)&0xFFFFFF:06x}") for t in types_all}

# Playback controls
with st.sidebar:
    st.markdown("## 🎞 Playback")
    if "play" not in st.session_state: st.session_state.play=False
    if "now"  not in st.session_state: st.session_state.now=window[0]
    step=st.slider("Step (s)",0.05,2.0,0.25,0.05)
    c1,c2,c3 = st.columns(3)
    if c1.button("▶"): st.session_state.play=True
    if c2.button("⏸"): st.session_state.play=False
    if c3.button("↺"): st.session_state.now = window[0]
    if st.session_state.play:
        st_autorefresh(interval=int(step*1000), key="auto")
        st.session_state.now = min(window[1], st.session_state.now + step)
    st.session_state.now = st.slider("Now", float(window[0]), float(window[1]),
                                     st.session_state.now, step)

# Apply filters
df = df_all[
    (df_all.type.isin(sel_types)) &
    (df_all.timestamp.between(window[0], window[1])) &
    (df_all.timestamp <= st.session_state.now)
]
df = safe_regex(df, regex)

G, edges = build_graph(df, min_w)
deg_c, btw_c, eig_c = centralities(G)

# Dashboard tab
with dash:
    st.markdown(f"<h3 style='color:{ACCENT}'>Dashboard</h3>",
                unsafe_allow_html=True)
    a,b,c,d,e = st.columns(5)
    a.metric("Events", f"{len(df)} / {len(df_all)}")
    b.metric("Nodes", G.number_of_nodes())
    c.metric("Edges", G.number_of_edges())
    density = nx.density(G) if G.number_of_nodes()>1 else 0
    d.metric("Density", f"{density:.3f}")
    e.metric("t (s)", f"{st.session_state.now:.2f}")

    st.subheader("Network")
    if not G.nodes: st.info("Graph empty.")
    else:
        net = Network(height=f"{NET_HEIGHT}px", width="100%", directed=True,
                      bgcolor="#1e1e1e" if theme=="dark" else "#fafafa",
                      font_color="#fff" if theme=="dark" else "#000")
        if not physics: net.toggle_physics(False)
        if layout=="hierarchical":
            net.set_options('{"layout":{"hierarchical":{"enabled":true,"direction":"UD"}}}')
        elif layout=="circular":
            circ = nx.circular_layout(G, scale=350)
        if physics and layout=="force":
            net.set_options(f'{{"physics":{{"barnesHut":{{"springLength":{spring},"gravitationalConstant":{-repel}}}}}}}')

        for n in G.nodes():
            label = cut(n, lablen)
            color = "#3d85c6" if "Runner" in n else "#6aa84f"
            if layout=="circular":
                x,y = circ[n]; net.add_node(n,label=label,color=color,x=x,y=y,fixed=True)
            else:
                net.add_node(n,label=label,color=color)
        for u,v,d in G.edges(data=True):
            typ = df[(df.source==u)&(df.target==v)].type.mode().iat[0]
            color = palette.get(typ,"#888")
            net.add_edge(u,v,value=d["weight"],
                         title=f"{u}→{v}<br>{typ} × {d['weight']}",
                         color=color, arrows="to" if arrows else "")
        html(net.generate_html(), height=NET_HEIGHT, scrolling=True)

# Inspector tab
with insp:
    st.markdown(f"<h3 style='color:{ACCENT}'>Inspector</h3>",
                unsafe_allow_html=True)
    if not G.nodes: st.info("Graph empty.")
    else:
        node = st.selectbox("Capability", sorted(G.nodes()))
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Degree",    G.degree(node))
        c2.metric("In",        G.in_degree(node))
        c3.metric("Out",       G.out_degree(node))
        c4.metric("Betweenness", f"{btw_c.get(node,0):.3f}")
        st.metric("Eigenvector", f"{eig_c.get(node,0):.3f}")
        st.write("Neighbours:", sorted(G.neighbors(node)))

        st.subheader("Shortest path")
        src = st.selectbox("Source", sorted(G.nodes()), key="src")
        dst = st.selectbox("Target", sorted(G.nodes()), key="dst")
        if st.button("Path"):
            try: st.success(" → ".join(nx.shortest_path(G, src, dst)))
            except nx.NetworkXNoPath: st.error("No path.")

# Data tab
with table:
    st.markdown(f"<h3 style='color:{ACCENT}'>Filtered events</h3>",
                unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV",
                       df.to_csv(index=False).encode(),
                       "events_filtered.csv")

# Analytics tab (with NEW charts)
with stat:
    st.markdown(f"<h3 style='color:{ACCENT}'>Analytics</h3>",
                unsafe_allow_html=True)
    if edges.empty:
        st.info("Edge list empty.")
    else:
        # 1) Edge-weight histogram
        st.subheader("Edge-weight histogram")
        st.bar_chart(edges.w)

        # 2) Node-degree histogram
        st.subheader("Node-degree histogram")
        degrees = [G.degree(n) for n in G.nodes()]
        st.bar_chart(pd.Series(degrees, name="deg"))

        # 3) Centrality scatter
        st.subheader("Centrality scatter  (degree vs betweenness)")
        if deg_c and btw_c:
            scatter_df = pd.DataFrame({
                "node": list(deg_c.keys()),
                "degree": list(deg_c.values()),
                "betweenness": [btw_c.get(n,0) for n in deg_c]
            })
            fig_scatter = go.Figure(go.Scatter(
                x=scatter_df.degree, y=scatter_df.betweenness,
                mode="markers+text", text=scatter_df.node,
                textposition="top center"))
            fig_scatter.update_layout(xaxis_title="Degree centrality",
                                      yaxis_title="Betweenness centrality")
            st.plotly_chart(fig_scatter, use_container_width=True)

        # 4) Event-text pie chart
        st.subheader("Event-text distribution")
        pie_counts = df.type.value_counts()
        if not pie_counts.empty:
            pie = go.Figure(go.Pie(labels=pie_counts.index,
                                   values=pie_counts.values,
                                   hole=.4))
            st.plotly_chart(pie, use_container_width=True)

        # 5) Heatmap & Sankey (unchanged)
        st.subheader("Transition heatmap")
        st.dataframe(edges.pivot_table(index="source", columns="target",
                                       values="w", fill_value=0))
        st.subheader("Sankey")
        node_list = list(G.nodes())
        src_i = [node_list.index(s) for s in edges.source]
        tgt_i = [node_list.index(t) for t in edges.target]
        st.plotly_chart(go.Figure(go.Sankey(
            node=dict(label=node_list, pad=15, thickness=18),
            link=dict(source=src_i, target=tgt_i, value=edges.w)
        )), use_container_width=True)
