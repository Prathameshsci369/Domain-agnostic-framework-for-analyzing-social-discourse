# step6_visualize.py
# STEP 6 — GENERATE INTERACTIVE HTML VISUALIZATION

import json
import os

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
INPUT_FILE = "output/final_knowledge_graph_and_scenario.json"
OUTPUT_DIR = "output"
OUTPUT_FILE = "knowledge_graph_viz.html"

# ─────────────────────────────────────────────
# HTML TEMPLATE
# ─────────────────────────────────────────────

# We use a placeholder {{DATA_PLACEHOLDER}} to safely inject the JSON
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Graph Visualization</title>
    <!-- Load Cytoscape.js from CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
    <style>
        body {
            margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1e1e24; color: #ffffff; display: flex; height: 100vh; overflow: hidden;
        }
        #graph-container {
            width: 70%; height: 100%; position: relative; background-color: #27272e;
        }
        #sidebar {
            width: 30%; height: 100%; background-color: #121217; padding: 20px; box-sizing: border-box;
            overflow-y: auto; border-left: 2px solid #3a3a45;
        }
        h1 { margin-top: 0; font-size: 1.5rem; color: #a78bfa; border-bottom: 1px solid #3a3a45; padding-bottom: 10px;}
        h2 { font-size: 1.2rem; color: #67e8f9; margin-top: 20px;}
        p { font-size: 0.95rem; line-height: 1.5; color: #d1d5db;}
        .stat-box { background: #27272e; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
        .stat-label { font-size: 0.8rem; color: #9ca3af; text-transform: uppercase;}
        .stat-value { font-size: 1.1rem; font-weight: bold; }
        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        .neutral { color: #facc15; }
        ul { padding-left: 20px; }
        li { margin-bottom: 8px; color: #d1d5db; }
        #node-details { margin-top: 30px; display: none; }
        .edge-list { margin-top: 10px; font-size: 0.9rem; }
    </style>
</head>
<body>

    <div id="graph-container"></div>

    <div id="sidebar">
        <h1>📊 Scenario Analysis</h1>
        <div id="scenario-content">
            <!-- Filled by JS -->
        </div>
        
        <div id="node-details">
            <h2>🔍 Node Details</h2>
            <div id="node-info"></div>
        </div>
    </div>

    <script>
        // Inject Data from Python
        const DATA = {{DATA_PLACEHOLDER}};

        // 1. Populate Sidebar with Scenario Analysis
        const scenario = DATA.scenario_analysis;
        const sentiment = DATA.metadata.overall_average_sentiment;
        
        document.getElementById('scenario-content').innerHTML = `
            <h2>${scenario.title || 'General Overview'}</h2>
            <p>${scenario.summary || 'No summary available.'}</p>
            
            <div class="stat-box">
                <div class="stat-label">Overall Sentiment</div>
                <div class="stat-value negative">${sentiment.negative}% Negative | ${sentiment.positive}% Positive</div>
            </div>

            <h2>🚀 Key Drivers</h2>
            <ul>
                ${(scenario.key_drivers || []).map(d => `<li>${d}</li>`).join('')}
            </ul>
        `;

        // 2. Initialize Cytoscape Graph
        const cy = cytoscape({
            container: document.getElementById('graph-container'),
            
            elements: [
                // Map Nodes
                ...DATA.knowledge_graph.nodes.map(n => ({
                    data: { id: n.name, label: n.name, type: n.type, mentions: n.mentions }
                })),
                // Map Edges
                ...DATA.knowledge_graph.edges.map((e, i) => ({
                    data: { 
                        id: `e${i}`, 
                        source: e.source, 
                        target: e.target, 
                        reason: e.reason, 
                        weight: e.weight || 1 
                    }
                }))
            ],

            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#1e1e24',
                        'font-size': '10px',
                        'background-color': '#666', // Default fallback
                        'width': 'mapData(mentions, 1, 10, 30, 80)',
                        'height': 'mapData(mentions, 1, 10, 30, 80)'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 'mapData(weight, 1, 5, 1, 5)',
                        'line-color': '#555',
                        'target-arrow-color': '#555',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'opacity': 0.7
                    }
                },
                // Specific Node Colors based on Type
                { selector: 'node[type = "Person"]', style: { 'background-color': '#5B8FF9' } },
                { selector: 'node[type = "Product"]', style: { 'background-color': '#F6BD16' } },
                { selector: 'node[type = "Organization"]', style: { 'background-color': '#5AD8A6' } },
                { selector: 'node[type = "Concept"]', style: { 'background-color': '#E86452' } },
                { selector: 'node[type = "Location"]', style: { 'background-color': '#6DC8EC' } },
                { selector: 'node[type = "Event"]', style: { 'background-color': '#945FB9' } },
                
                // Highlight classes
                { selector: '.highlighted', style: { 'background-color': '#ff0', 'line-color': '#ff0', 'target-arrow-color': '#ff0', 'opacity': 1 } },
                { selector: '.dimmed', style: { 'opacity': 0.2 } }
            ],

            layout: {
                name: 'cose', // Good force-directed layout
                padding: 30,
                nodeRepulsion: 8000
            }
        });

        // 3. Interactivity: Click on Node to see details
        cy.on('tap', 'node', function(evt){
            const node = evt.target;
            const connectedEdges = node.connectedEdges();
            
            // Dim everything
            cy.elements().addClass('dimmed').removeClass('highlighted');
            // Highlight selected node and its edges
            node.removeClass('dimmed').addClass('highlighted');
            connectedEdges.removeClass('dimmed').addClass('highlighted');
            connectedEdges.connectedNodes().removeClass('dimmed').addClass('highlighted');

            // Show connections in sidebar
            let connectionsHtml = '';
            connectedEdges.forEach(edge => {
                const target = edge.target();
                const source = edge.source();
                const otherNode = (source.id() === node.id()) ? target : source;
                connectionsHtml += `<div class="edge-list"><b>${otherNode.id()}</b>: ${edge.data('reason')}</div><hr style="border-color:#333">`;
            });

            document.getElementById('node-info').innerHTML = `
                <div class="stat-box">
                    <div class="stat-label">Entity</div>
                    <div class="stat-value">${node.data('label')}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Type | Mentions</div>
                    <div class="stat-value">${node.data('type')} | ${node.data('mentions')}x</div>
                </div>
                <h3 style="margin-top:15px; color:#a78bfa;">Connections:</h3>
                ${connectionsHtml}
            `;
            document.getElementById('node-details').style.display = 'block';
        });

        // Click on background to reset
        cy.on('tap', function(evt){
            if(evt.target === cy){
                cy.elements().removeClass('dimmed').removeClass('highlighted');
                document.getElementById('node-details').style.display = 'none';
            }
        });

    </script>
</body>
</html>
"""

# ─────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────

def run_visualizer(input_path: str, output_path: str):
    print("\n" + "="*50)
    print("STEP 6 — HTML VISUALIZATION GENERATOR")
    print("="*50)

    if not os.path.exists(input_path):
        print(f"❌ ERROR: Input file not found at {input_path}. Run step5 first.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    print("⏳ Generating HTML with embedded data...")
    
    # Convert JSON to a safe JavaScript string format
    json_js_string = json.dumps(graph_data, indent=None, ensure_ascii=False)
    
    # Inject data into HTML template
    final_html = HTML_TEMPLATE.replace("{{DATA_PLACEHOLDER}}", json_js_string)

    # Save HTML file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    full_path = os.path.abspath(output_path)
    print(f"\n✅ Successfully generated visualization!")
    print(f"📁 File location: {full_path}")
    print("\n💡 HOW TO VIEW: Open your file manager, navigate to the 'output' folder, and DOUBLE-CLICK 'knowledge_graph_viz.html' to open it in your browser (Chrome/Firefox recommended).\n")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, INPUT_FILE)
    output_file = os.path.join(base_dir, OUTPUT_DIR, OUTPUT_FILE)
    
    run_visualizer(input_file, output_file)