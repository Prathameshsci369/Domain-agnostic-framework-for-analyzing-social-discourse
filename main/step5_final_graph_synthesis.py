# step5_lens_analysis.py
# STEP 5 — MULTI-LENS AGENT ANALYSIS (Robust LLM Calling)

import json
import os
import sys
import time

# ─────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────
try:
    from neo4j import GraphDatabase
    from llama_cpp import Llama
except ImportError:
    print("❌ ERROR: Missing libraries.")
    print("Run: pip install neo4j llama-cpp-python")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345"  # <--- UPDATE THIS

MODEL_PATH = "/home/anand/Downloads/Qwen3.5-4B-Q4_K_M.gguf"
OUTPUT_FILE = "output/step5_lens_analysis.json"

# The 7 Cognitive Lenses Configuration
LENSES = {
    "psychology": {
        "role": "Psychologist",
        "focus": "Analyze the crowd behavior, herd mentality, emotional triggers, and individual vs group dynamics."
    },
    "economics": {
        "role": "Economist",
        "focus": "Analyze financial incentives, resource flows, market crashes, and economic power structures."
    },
    "power": {
        "role": "Political Strategist",
        "focus": "Analyze hierarchy, control mechanisms, influence, and state vs individual power."
    },
    "technology": {
        "role": "Technologist",
        "focus": "Analyze technological disruption, automation, and the role of tools in the event."
    },
    "history": {
        "role": "Historian",
        "focus": "Compare this event with past historical patterns. What does history suggest will happen next?"
    },
    "ethics": {
        "role": "Ethicist",
        "focus": "Evaluate the moral framing, rights violations, and ethical dilemmas present."
    },
    "statistics": {
        "role": "Statistician",
        "focus": "Evaluate the data reliability. Identify sampling bias or statistical anomalies."
    }
}

# ─────────────────────────────────────────────
# ROBUST LLM CLIENT CLASS
# ─────────────────────────────────────────────

class LLMClient:
    """
    A clean wrapper for llama-cpp to avoid repetitive error handling.
    """
    def __init__(self, model_path, n_ctx=8192, n_threads=8, n_gpu_layers=-1):
        print(f"🔄 Initializing Robust LLM Client...")
        self.model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        print("✅ LLM Client Ready.")

    def generate(self, system_prompt: str, user_prompt: str, temperature=0.3, max_tokens=1024) -> str:
        """
        Generates text safely. Returns a string.
        """
        try:
            response = self.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Safe extraction of content
            # Handles both dict and potential object returns from library updates
            if isinstance(response, dict):
                return response['choices'][0]['message']['content'].strip()
            else:
                return str(response.choices[0].message.content).strip()
                
        except Exception as e:
            print(f"⚠️ LLM Generation Error: {e}")
            return "Error: Analysis failed."

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Generates and parses JSON safely.
        """
        raw_text = self.generate(system_prompt, user_prompt, temperature=0.1)
        
        # Clean markdown if present
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # Fallback: Return the raw text if JSON parsing fails
            print("⚠️ JSON Parse failed, returning raw text.")
            return {"raw_analysis": raw_text, "error": "json_parse_failed"}

# ─────────────────────────────────────────────
# GRAPH FETCHER
# ─────────────────────────────────────────────

def get_graph_summary(driver):
    """
    Queries Neo4j to get a text summary of the most important entities and relations.
    """
    query = """
    MATCH (n)-[r]->(m)
    WITH n, r, m
    ORDER BY r.weight DESC
    LIMIT 50
    RETURN n.name as source, n.type as s_type, r.relation as relation, 
           m.name as target, m.type as t_type, r.evidence as evidence
    """
    records = driver.session().run(query)
    
    summary_lines = []
    for record in records:
        line = f"{record['source']} ({record['s_type']}) --[{record['relation']}]--> {record['target']} ({record['t_type']})"
        summary_lines.append(line)
        
    return "\n".join(summary_lines)

# ─────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────

def run_step5():
    print("\n" + "="*50)
    print("STEP 5 — MULTI-LENS AGENT ANALYSIS")
    print("="*50)

    # 1. Initialize Clients
    try:
        llm_client = LLMClient(MODEL_PATH, n_threads=8, n_gpu_layers=-1)
        db = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("✅ Systems Connected.")
    except Exception as e:
        print(f"❌ Initialization Error: {e}")
        return

    # 2. Fetch Data from Graph
    print("📊 Fetching Graph Summary...")
    graph_data = get_graph_summary(db)
    
    if not graph_data:
        print("❌ No data found in Neo4j. Run Step 4 first.")
        return

    print(f"📝 Graph Data Preview:\n{graph_data[:300]}...\n")

    # 3. Run Lens Agents
    final_report = {}
    
    for lens_key, lens_config in LENSES.items():
        print(f"🧠 Analyzing via {lens_key.upper()} Lens...")
        
        # Construct Prompt
        system_msg = f"You are an expert {lens_config['role']}. {lens_config['focus']}"
        user_msg = f"""
        Analyze the following knowledge graph data based on your expertise.
        
        GRAPH DATA:
        {graph_data}
        
        Provide your analysis in the following JSON format:
        {{
            "lens": "{lens_key}",
            "summary": "A 2-sentence high-level summary.",
            "key_insight": "The most critical finding from your perspective.",
            "risk_level": "Low / Medium / High",
            "prediction": "What does this data suggest will happen next?"
        }}
        """
        
        # Call LLM via Robust Client
        result = llm_client.generate_json(system_msg, user_msg)
        final_report[lens_key] = result
        
        print(f"   ✅ {lens_key} complete.")
        time.sleep(0.5) # Small pause to prevent overheating/CPU thrashing

    # 4. Save Results
    db.close()
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_report, f, indent=2)

    print("\n" + "-"*50)
    print("LENS ANALYSIS COMPLETE")
    print("-"*50)
    print(f"📁 Report saved to: {OUTPUT_FILE}")
    print("💡 Next Step: Generate Scenarios based on these lenses.")
    print("✅ Step 5 complete.\n")

if __name__ == "__main__":
    run_step5()