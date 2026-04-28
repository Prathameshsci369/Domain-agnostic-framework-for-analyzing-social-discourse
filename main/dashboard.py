# app/dashboard.py
# MULTIVERSE INSIGHTS DASHBOARD

import streamlit as st
import json
import os
import sys

# Add parent directory to path to import config if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from neo4j import GraphDatabase
    import networkx as nx
    from pyvis.network import Network
except ImportError:
    st.error("Missing libraries. Run: pip install streamlit pyvis networkx neo4j")
    st.stop()

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345"  # UPDATE THIS
REPORT_FILE = "/home/anand/Videos/multiverse_insights_2.0/new_steps/output/final_strategic_report.json"

# ─────────────────────────────────────────────
# PAGE SETUP
# ─────────────────────────────────────────────
st.set_page_config(page_title="Multiverse Insights", layout="wide", page_icon="🌌")

# Custom CSS for better readability and styling
st.markdown("""
<style>
    /* Root and overall styling */
    :root {
        --primary-text: #1a1a1a !important;
        --secondary-text: #2c3e50 !important;
        --light-bg: #f0f2f6 !important;
    }
    
    /* Overall page background */
    body, .main, .block-container {
        background-color: #f0f2f6 !important;
    }
    
    /* Headers - LARGE and BOLD */
    h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a !important;
    }
    
    h1 {
        font-size: 3.2rem !important;
        font-weight: 800 !important;
        color: #0d47a1 !important;
        margin-bottom: 1rem !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    
    h2 {
        font-size: 2.6rem !important;
        font-weight: 700 !important;
        color: #1a237e !important;
        margin-top: 2rem !important;
        margin-bottom: 1.5rem !important;
        border-bottom: 3px solid #1976d2 !important;
        padding-bottom: 0.5rem !important;
    }
    
    h3 {
        font-size: 2.1rem !important;
        font-weight: 700 !important;
        color: #283593 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Main text and paragraphs */
    p {
        font-size: 1.25rem !important;
        line-height: 1.8 !important;
        color: #1a1a1a !important;
    }
    
    /* Strong emphasis */
    strong, b {
        color: #0d47a1 !important;
        font-weight: 700 !important;
    }
    
    /* Links */
    a {
        color: #1565c0 !important;
        text-decoration: underline !important;
    }
    
    /* Alert boxes */
    .stAlert {
        border-radius: 8px !important;
        padding: 1.5rem !important;
        font-size: 1.15rem !important;
    }
    
    .stInfo {
        background-color: #c8e6f5 !important;
        border-left: 5px solid #0277bd !important;
        color: #01579b !important;
    }
    
    .stWarning {
        background-color: #ffe8b6 !important;
        border-left: 5px solid #f57f17 !important;
        color: #e65100 !important;
    }
    
    .stError {
        background-color: #ffcdd2 !important;
        border-left: 5px solid #c62828 !important;
        color: #b71c1c !important;
    }
    
    .stSuccess {
        background-color: #c8e6c9 !important;
        border-left: 5px solid #2e7d32 !important;
        color: #1b5e20 !important;
    }
    
    /* Metric labels */
    [data-testid="stMetricLabel"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #0d47a1 !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #1a1a1a !important;
    }
    
    /* Captions */
    .stCaption {
        font-size: 1.2rem !important;
        color: #424242 !important;
    }
    
    /* Columns content */
    [data-testid="column"] {
        background-color: #ffffff !important;
        padding: 2rem !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12) !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    /* All text elements */
    span, div {
        color: #1a1a1a !important;
    }
    
    /* Markdown text */
    .markdown-text-container {
        font-size: 1.2rem !important;
        color: #1a1a1a !important;
    }
    
    /* Block container */
    .block-container {
        padding: 2rem 2rem !important;
        max-width: 1400px !important;
        background-color: #f0f2f6 !important;
    }
    
    /* Horizontal divider */
    hr {
        border-top: 3px solid #1976d2 !important;
        margin: 2rem 0 !important;
    }
    
    /* Scenario cards */
    .scenario-card {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        margin: 0 0.5rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12) !important;
        border: 2px solid #e0e0e0 !important;
        min-height: 450px !important;
        display: flex !important;
        flex-direction: column !important;
    }
    
    .scenario-header {
        text-align: center !important;
        padding: 1rem !important;
        border-radius: 8px !important;
        margin-bottom: 1.5rem !important;
        font-weight: 800 !important;
    }
    
    .scenario-title {
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        margin: 1rem 0 !important;
    }
    
    .scenario-probability {
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        margin: 1rem 0 !important;
    }
    
    .scenario-description {
        font-size: 1.1rem !important;
        line-height: 1.8 !important;
        color: #1a1a1a !important;
        flex-grow: 1 !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    
    /* Warning signal cards */
    .warning-signal {
        background-color: #ffcdd2 !important;
        border-left: 5px solid #c62828 !important;
        padding: 1.5rem !important;
        border-radius: 8px !important;
        margin-bottom: 1.2rem !important;
        font-size: 1.15rem !important;
        color: #b71c1c !important;
        font-weight: 600 !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
    }
    
    .warning-signal strong {
        color: #c62828 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌌 Multiverse Insights 2.0")
st.markdown("<div style='font-size: 1.6rem; color: #1a1a1a; margin-bottom: 1.5rem; font-weight: 600;'>Real-Time Causal Intelligence Engine</div>", unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 1: LOAD STRATEGIC REPORT
# ─────────────────────────────────────────────
st.header("📊 Strategic Analysis Report")

if os.path.exists(REPORT_FILE):
    with open(REPORT_FILE, "r") as f:
        report = json.load(f)
    
    # Display Topic with larger font
    topic = report.get('event_topic', 'Unknown Event')
    st.markdown(f"<div style='font-size: 2rem; font-weight: 800; color: #0d47a1; margin-bottom: 2rem; background-color: #e3f2fd; padding: 1.5rem; border-radius: 8px; border-left: 5px solid #1976d2;'>📌 Topic: {topic}</div>", unsafe_allow_html=True)
    
    # Use Columns for Summary
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div style='font-size: 1.6rem; font-weight: 700; color: #0d47a1; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 3px solid #0d47a1;'>🕰️ Past Reconstruction</div>", unsafe_allow_html=True)
        st.info(report.get('past_reconstruction', 'N/A'))
        
    with col2:
        st.markdown("<div style='font-size: 1.6rem; font-weight: 700; color: #e65100; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 3px solid #e65100;'>📍 Current State</div>", unsafe_allow_html=True)
        st.warning(report.get('current_state', 'N/A'))

    # Scenarios
    st.markdown("<div style='font-size: 2rem; font-weight: 800; color: #0d47a1; margin-top: 2.5rem; margin-bottom: 2rem; background-color: #e3f2fd; padding: 1.5rem; border-radius: 8px; border-left: 5px solid #1976d2;'>🔮 Future Scenarios</div>", unsafe_allow_html=True)
    
    s_a = report.get('scenario_a', {})
    s_b = report.get('scenario_b', {})
    s_c = report.get('scenario_c', {})
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("""
        <div class="scenario-card">
            <div class="scenario-header" style="background-color: #bbdefb; color: #0d47a1;">Scenario A</div>
            <div class="scenario-title" style="color: #0d47a1;">""" + s_a.get('name', 'N/A') + """</div>
            <div class="scenario-probability" style="color: #1565c0;">📊 Probability: """ + s_a.get('probability', 'N/A') + """</div>
            <div class="scenario-description">""" + s_a.get('description', 'No description available') + """</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown("""
        <div class="scenario-card">
            <div class="scenario-header" style="background-color: #ffe0b2; color: #e65100;">Scenario B</div>
            <div class="scenario-title" style="color: #e65100;">""" + s_b.get('name', 'N/A') + """</div>
            <div class="scenario-probability" style="color: #f57f17;">📊 Probability: """ + s_b.get('probability', 'N/A') + """</div>
            <div class="scenario-description">""" + s_b.get('description', 'No description available') + """</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown("""
        <div class="scenario-card">
            <div class="scenario-header" style="background-color: #c8e6c9; color: #2e7d32;">Scenario C</div>
            <div class="scenario-title" style="color: #2e7d32;">""" + s_c.get('name', 'N/A') + """</div>
            <div class="scenario-probability" style="color: #558b2f;">📊 Probability: """ + s_c.get('probability', 'N/A') + """</div>
            <div class="scenario-description">""" + s_c.get('description', 'No description available') + """</div>
        </div>
        """, unsafe_allow_html=True)

    # Warning Signals
    st.markdown("<div style='font-size: 2rem; font-weight: 800; color: #c62828; margin-top: 2.5rem; margin-bottom: 2rem; background-color: #ffebee; padding: 1.5rem; border-radius: 8px; border-left: 5px solid #c62828;'>🚨 Early Warning Signals</div>", unsafe_allow_html=True)
    
    signals = report.get('early_warning_signals', [])
    for i, signal in enumerate(signals, 1):
        st.markdown(f"""
        <div class="warning-signal">
            <strong>⚠️ Signal {i}:</strong> {signal}
        </div>
        """, unsafe_allow_html=True)
        
else:
    st.warning("No report found. Please run `step6_scenario_generator.py` first.")

st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 2: VISUALIZE KNOWLEDGE GRAPH
# ─────────────────────────────────────────────
st.header("🕸️ Knowledge Graph Visualization")

st.markdown("""
<div style='font-size: 1.3rem; color: #0d47a1; background-color: #bbdefb; padding: 1.5rem; border-radius: 8px; border-left: 5px solid #0d47a1; margin-bottom: 2rem; font-weight: 600;'>
    <strong>📊 Interactive Graph Display:</strong> This visualization shows the top 50 most influential entities and relationships based on connection weight. <br><br>
    🖱️ <strong>Controls:</strong> Zoom with mouse wheel, drag to pan, click nodes to highlight connections.
</div>
""", unsafe_allow_html=True)

def get_graph_data():
    """Fetches data from Neo4j and converts to PyVis Network."""
    driver = None
    session = None
    try:
        # Create driver with explicit encryption setting
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            encrypted=False,
            connection_timeout=30
        )
        session = driver.session()
        
        # Test query first
        session.run("RETURN 1")
        
        # Query Top Nodes/Edges with better structure
        query = """
        MATCH (n)-[r]->(m)
        WITH n, r, m, r.weight as weight
        ORDER BY weight DESC
        LIMIT 100
        RETURN n.name as source, n.type as s_type, r.relation as relation, 
               m.name as target, m.type as t_type, r.weight as weight
        """
        result = session.run(query)
        records = list(result)
        
        # Build NetworkX Graph with better attributes
        G = nx.Graph()
        
        # Color mapping for different entity types
        color_map = {
            "Person": "#FF6B6B",
            "Organization": "#4ECDC4",
            "Concept": "#45B7D1",
            "Location": "#FFA07A",
            "Event": "#98D8C8",
            "Unknown": "#95A5A6"
        }
        
        # Track node degrees for sizing
        node_weights = {}
        
        for record in records:
            s = record['source']
            t = record['target']
            w = record['weight'] if record['weight'] else 1
            rel = record['relation']
            s_type = record['s_type'] if record['s_type'] else "Unknown"
            t_type = record['t_type'] if record['t_type'] else "Unknown"
            
            # Track weights for sizing
            node_weights[s] = node_weights.get(s, 0) + w
            node_weights[t] = node_weights.get(t, 0) + w
            
            # Add nodes with styling
            G.add_node(
                s, 
                title=f"{s}\nType: {s_type}",
                group=s_type,
                color=color_map.get(s_type, color_map["Unknown"]),
                size=20
            )
            G.add_node(
                t, 
                title=f"{t}\nType: {t_type}",
                group=t_type,
                color=color_map.get(t_type, color_map["Unknown"]),
                size=20
            )
            
            # Add edge with weight
            G.add_edge(s, t, title=f"{rel}", weight=w, label=rel)
        
        # Normalize node sizes based on weight
        if node_weights:
            max_weight = max(node_weights.values())
            min_weight = min(node_weights.values())
            weight_range = max_weight - min_weight if max_weight > min_weight else 1
            
            for node in G.nodes():
                normalized_weight = (node_weights.get(node, 0) - min_weight) / weight_range
                size = 25 + (normalized_weight * 50)  # Size between 25-75
                G.nodes[node]['size'] = size
        
        return G, None
        
    except Exception as e:
        import traceback
        error_msg = f"Failed to connect to Neo4j: {e}\n\nTraceback: {traceback.format_exc()}"
        return nx.Graph(), error_msg
    finally:
        if session:
            try:
                session.close()
            except:
                pass
        if driver:
            try:
                driver.close()
            except:
                pass

# Generate Visualization
G, error_msg = get_graph_data()

if error_msg:
    st.error(error_msg)
else:
    # Debug info
    debug_col1, debug_col2, debug_col3 = st.columns(3)
    with debug_col1:
        st.metric("Nodes Found", G.number_of_nodes())
    with debug_col2:
        st.metric("Edges Found", G.number_of_edges())
    with debug_col3:
        st.metric("Status", "✅ Ready" if G.number_of_nodes() > 0 else "❌ No Data")

if G.number_of_nodes() > 0:
    try:
        # PyVis Setup - simplified and robust
        net = Network(
            height="900px", 
            width="100%", 
            bgcolor="#f8f9fa",
            font_color="#1a1a1a",
            directed=False
        )
        
        # Add nodes with explicit properties
        for node in G.nodes():
            node_data = G.nodes[node]
            net.add_node(
                node,
                label=str(node),
                title=node_data.get('title', str(node)),
                color=node_data.get('color', '#4ECDC4'),
                size=node_data.get('size', 30),
                font={'size': 18, 'color': '#1a1a1a'},
                shadow=True
            )
        
        # Add edges with explicit properties  
        for edge in G.edges(data=True):
            source, target, data = edge
            net.add_edge(
                source,
                target,
                title=data.get('title', 'relation'),
                label=data.get('label', ''),
                weight=data.get('weight', 1),
                color='#888888',
                width=2,
                font={'size': 14, 'color': '#1a1a1a'},
                smooth=True
            )
        
        # Set physics options - STABLE version
        physics_config = {
            "physics": {
                "enabled": True,
                "barnesHut": {
                    "gravitationalConstant": -20000,
                    "centralGravity": 0.2,
                    "springLength": 250,
                    "springConstant": 0.01,
                    "damping": 0.8
                },
                "maxVelocity": 50,
                "solver": "barnesHut",
                "timestep": 0.5,
                "minVelocity": 0.5,
                "adaptiveTimestep": True
            },
            "nodes": {
                "font": {
                    "size": 18,
                    "face": "Arial, sans-serif",
                    "color": "#1a1a1a",
                    "strokeWidth": 2,
                    "strokeColor": "#ffffff"
                },
                "borderWidth": 3,
                "borderWidthSelected": 5,
                "shadow": {
                    "enabled": True,
                    "color": "rgba(0,0,0,0.3)",
                    "size": 15,
                    "x": 5,
                    "y": 5
                }
            },
            "edges": {
                "color": {
                    "color": "#888888",
                    "highlight": "#1976d2",
                    "opacity": 0.8
                },
                "font": {
                    "size": 15,
                    "color": "#1a1a1a",
                    "strokeWidth": 2,
                    "strokeColor": "#ffffff",
                    "bold": {"size": 16}
                },
                "smooth": {
                    "enabled": True,
                    "type": "cubicBezier"
                },
                "width": 2,
                "widthSelectionMultiplier": 3
            },
            "interaction": {
                "navigationButtons": True,
                "keyboard": True,
                "zoomView": True,
                "dragView": True,
                "hover": True,
                "hideEdgesOnDrag": False
            }
        }
        
        net.set_options(str(physics_config).replace("'", '"').replace("True", "true").replace("False", "false"))
        
        # Save and display
        graph_path = '/tmp/network_graph.html'
        net.save_graph(graph_path)
        
        # Read the HTML file
        with open(graph_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Display with container styling
        st.markdown("""
        <style>
            .graph-container {
                border: 3px solid #1976d2;
                border-radius: 12px;
                overflow: hidden;
                background: white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
        </style>
        <div class="graph-container">
        """, unsafe_allow_html=True)
        
        st.components.v1.html(html_content, height=920, scrolling=False)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Graph statistics
        st.markdown("---")
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; background: #bbdefb; border-radius: 8px; font-size: 1.4rem; font-weight: 700; color: #0d47a1;'>
                📍 Nodes<br><span style='font-size: 2.2rem;'>{G.number_of_nodes()}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with stat_col2:
            st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; background: #ffe0b2; border-radius: 8px; font-size: 1.4rem; font-weight: 700; color: #e65100;'>
                🔗 Edges<br><span style='font-size: 2.2rem;'>{G.number_of_edges()}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with stat_col3:
            avg_degree = (2 * G.number_of_edges()) / max(G.number_of_nodes(), 1)
            st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; background: #c8e6c9; border-radius: 8px; font-size: 1.4rem; font-weight: 700; color: #2e7d32;'>
                📊 Avg Degree<br><span style='font-size: 2.2rem;'>{avg_degree:.1f}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with stat_col4:
            density = nx.density(G)
            st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; background: #ffcdd2; border-radius: 8px; font-size: 1.4rem; font-weight: 700; color: #c62828;'>
                🔍 Density<br><span style='font-size: 2.2rem;'>{density:.3f}</span>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as viz_error:
        st.error(f"Error rendering graph: {viz_error}")
        import traceback
        st.error(traceback.format_exc())
        
        # Fallback: Show graph as text
        st.warning("Graph visualization failed. Here's the network data:")
        st.write(f"**Nodes**: {list(G.nodes())[:10]}...")
        st.write(f"**Edges**: {list(G.edges())[:5]}...")
    
else:
    if not error_msg:
        st.warning("""
        ⚠️ **No Graph Data Available**
        
        The Neo4j database is connected but contains no entity relationships yet.
        Please ensure you have:
        1. Run all previous steps (step1-step4)
        2. Extracted entities and relations
        3. Populated Neo4j with graph data
        """)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align: center; font-size: 1.3rem; color: #0d47a1; padding: 2rem 0; font-weight: 700; background-color: #e3f2fd; margin: 2rem -2rem 0 -2rem; padding: 2rem;'>
    <strong>🌌 Multiverse Insights 2.0</strong> | Local-First | Privacy Aware | Powered by Neo4j & LLaMA
</div>
""", unsafe_allow_html=True)