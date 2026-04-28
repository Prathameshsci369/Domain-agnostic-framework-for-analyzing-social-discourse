# step4_graph_builder_cpp.py
# STEP 4 — GRAPH BUILDER (RESUME + BACKUP + SMART PARSING)

import json
import os
import sys
import time
import re
import gc 
from datetime import datetime

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
INPUT_FILE = "output/step3_llm_ready.json"
PROGRESS_FILE = "output/step4_progress.json"
EXTRACTED_DATA_FILE = "output/step4_extracted_data.json"
FINAL_SUMMARY_FILE = "output/step4_summary.json"

# Neo4j Direct Connection
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345"  # <--- UPDATE THIS WITH YOUR NEO4J PASSWORD

# Local LLM Configuration
MODEL_PATH = "/home/anand/Downloads/Qwen3.5-4B-Q4_K_M.gguf"
CONTEXT_WINDOW = 16384

# ─────────────────────────────────────────────
# INITIALIZE LOCAL LLM
# ─────────────────────────────────────────────
print(f"🔄 Loading Local Model: {MODEL_PATH}...", flush=True)
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=CONTEXT_WINDOW,
    n_threads=8,
    n_gpu_layers=-1,
    verbose=False
)
print("✅ Model Loaded Successfully.", flush=True)

# ─────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, query, parameters=None):
        session = self.driver.session()
        response = list(session.run(query, parameters))
        session.close()
        return response

# ─────────────────────────────────────────────
# DATA MANAGER
# ─────────────────────────────────────────────

class DataManager:
    def __init__(self, progress_file, data_file):
        self.progress_file = progress_file
        self.data_file = data_file
        os.makedirs(os.path.dirname(self.progress_file) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(self.data_file) or ".", exist_ok=True)

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    last_idx = data.get("last_processed_index", -1)
                    print(f"🚀 Resuming from Batch {last_idx + 1} (Last saved: {last_idx})", flush=True)
                    return last_idx + 1
            except Exception as e:
                print(f"⚠️  Error reading progress file: {e}. Starting from scratch.", flush=True)
                return 0
        return 0

    def save_progress(self, index, total_batches):
        data = {
            "last_processed_index": index,
            "timestamp": datetime.now().isoformat(),
            "total_batches": total_batches
        }
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save progress: {e}", flush=True)

    def save_batch_data(self, batch_index, extraction_data):
        """Saves extracted data to JSON immediately."""
        current_data = []
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    current_data = json.load(f)
            except:
                current_data = []
        
        current_data = [d for d in current_data if d.get("batch_index") != batch_index]
        
        record = {
            "batch_index": batch_index,
            "timestamp": datetime.now().isoformat(),
            "entities": extraction_data.get("entities", []),
            "relations": extraction_data.get("relations", [])
        }
        current_data.append(record)
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(current_data, f, indent=2)
            print(f"💾 Data Backup Saved: Batch {batch_index}", flush=True)
        except Exception as e:
            print(f"⚠️  Warning: Could not save data backup: {e}", flush=True)

    def cleanup(self):
        files_to_remove = [self.progress_file]
        for f in files_to_remove:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"🧹 Cleaned up: {f}", flush=True)
                except Exception as e:
                    print(f"⚠️  Could not remove {f}: {e}", flush=True)

# ─────────────────────────────────────────────
# EXTRACTION LOGIC
# ─────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a Knowledge Graph Extractor. Extract Entities and Relations from the text.

CONSTRAINTS:
1. Extract ONLY the top 15 most important Entities.
2. Extract ONLY the top 20 most important Relations.
3. Return ONLY a valid JSON object. No markdown, no explanations.

Format:
{{
  "entities": [
    {{"name": "EntityName", "type": "Person|Organization|Location|Concept"}}
  ],
  "relations": [
    {{
      "source": "Entity A", 
      "target": "Entity B", 
      "relation": "verb phrase", 
      "evidence": "short quote"
    }}
  ]
}}

TEXT:
{text}

JSON:"""

def fix_truncated_json(json_str: str) -> dict:
    s = json_str.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    check_limit = min(len(s), 500) 
    for i in range(check_limit):
        truncated = s[:-i] if i > 0 else s
        for suffix in ["}", "]", "]}"]:
            try:
                return json.loads(truncated + suffix)
            except:
                continue
    return {"entities": [], "relations": []}

def call_llm_extraction(text: str) -> dict:
    try:
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise JSON data extractor. Output ONLY valid JSON."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}
            ],
            temperature=0.1,
            max_tokens=8192, 
        )
        
        content = ""
        if isinstance(response, dict):
            content = response['choices'][0]['message']['content'].strip()
        else:
            content = str(response.choices[0].message.content).strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        start_idx = content.find('{')
        if start_idx == -1:
            return {"entities": [], "relations": []}
            
        json_str = content[start_idx:]
        parsed = fix_truncated_json(json_str)
        
        if "entities" not in parsed or "relations" not in parsed:
            return {"entities": [], "relations": []}
            
        return parsed

    except Exception as e:
        print(f"   ⚠️  Critical LLM Error: {e}", flush=True)
        return {"entities": [], "relations": []}

# ─────────────────────────────────────────────
# GRAPH POPULATION
# ─────────────────────────────────────────────

def add_to_graph(tx, source, target, relation, evidence, s_type, t_type):
    query = """
    MERGE (s:Entity {name: $source})
    ON CREATE SET s.type = $s_type, s.first_seen = timestamp()
    ON MATCH SET s.count = coalesce(s.count, 0) + 1

    MERGE (t:Entity {name: $target})
    ON CREATE SET t.type = $t_type, t.first_seen = timestamp()
    ON MATCH SET t.count = coalesce(t.count, 0) + 1

    MERGE (s)-[r:RELATES_TO]->(t)
    ON CREATE SET r.relation = $relation, r.evidence = $evidence, r.weight = 1
    ON MATCH SET r.weight = coalesce(r.weight, 0) + 1
    """
    tx.run(query, 
           source=source, target=target, relation=relation, evidence=evidence,
           s_type=s_type, t_type=t_type)

def process_batch(db_conn, data_mgr, batch_data):
    text_content = batch_data.get("text_for_llm", "")
    batch_id = batch_data.get("batch_index")
    
    print(f"   🔍 Processing Batch {batch_id}...", flush=True)
    
    extraction = call_llm_extraction(text_content)
    entities = extraction.get("entities", [])
    relations = extraction.get("relations", [])
    
    data_mgr.save_batch_data(batch_id, extraction)
    
    if not entities and not relations:
        print(f"      ℹ️  No entities/relations found in Batch {batch_id}.", flush=True)
        return 0

    count = 0
    skipped_count = 0
    with db_conn.driver.session() as session:
        for rel in relations:
            # SMART PARSING: Handle LLM hallucinations where it uses 'name' instead of 'source'
            source = rel.get("source") or rel.get("name")
            target = rel.get("target")
            
            if not source or not target:
                skipped_count += 1
                continue
            
            relation_type = rel.get("relation")
            if not relation_type or relation_type.strip() == "":
                skipped_count += 1
                continue
                
            evidence = rel.get("evidence", "")
            
            s_type = next((e['type'] for e in entities if e['name'] == source), "Unknown")
            t_type = next((e['type'] for e in entities if e['name'] == target), "Unknown")
            
            try:
                session.execute_write(add_to_graph, source, target, relation_type, evidence, s_type, t_type)
                count += 1
            except Exception as e:
                print(f"      ⚠️ DB Write Error: {e}", flush=True)
                skipped_count += 1
    
    if skipped_count > 0:
        print(f"      ✅ Batch {batch_id} Done. Relations: {count} (Skipped invalid: {skipped_count})", flush=True)
    else:
        print(f"      ✅ Batch {batch_id} Done. Relations: {count}", flush=True)
    return count

# ─────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────

class EntityTracker:
    def __init__(self):
        pass

def run_step4():
    print("\n" + "="*50, flush=True)
    print("STEP 4 — GRAPH CONSTRUCTION (RESUME + BACKUP)", flush=True)
    print("="*50, flush=True)

    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.", flush=True)
        return

    data_mgr = DataManager(PROGRESS_FILE, EXTRACTED_DATA_FILE)

    # 1. Connect to Neo4j
    try:
        db = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        print("✅ Connected to Neo4j (Direct).", flush=True)
        db.query("RETURN 1")
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}", flush=True)
        return

    # 2. Load Data
    with open(INPUT_FILE, "r") as f:
        batches = json.load(f)
    
    total_batches = len(batches)
    print(f"📂 Total Batches in File: {total_batches}", flush=True)

    # 3. Resume Logic
    start_index = data_mgr.load_progress()
    
    if start_index == 0:
        print("🚀 Starting fresh process.", flush=True)
    
    tracker = EntityTracker()
    total_relations = 0
    start_time = time.time()
    
    for i in range(start_index, total_batches):
        batch = batches[i]
        try:
            count = process_batch(db, data_mgr, batch)
            total_relations += count
            
            data_mgr.save_progress(i, total_batches)
            print(f"💾 Progress Index Saved: Batch {i+1}/{total_batches}", flush=True)
            
            # Stability
            time.sleep(2) 
            gc.collect()
            
        except KeyboardInterrupt:
            print("\n⚠️  Process interrupted by user. Progress saved.", flush=True)
            break
        except Exception as e:
            print(f"   ❌ Critical Error in batch {i}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            print("   ⚠️  Stopping execution. Data is backed up in JSON.", flush=True)
            break

    # 4. Completion Check
    if start_index > 0 and (start_index - 1) == (total_batches - 1):
         print("✅ Data already fully processed.", flush=True)
    elif start_index == total_batches:
        data_mgr.cleanup()
        
        duration = time.time() - start_time
        db.close()
        
        summary = {
            "status": "completed",
            "total_batches_processed": total_batches,
            "total_relations_added": total_relations,
            "duration_seconds": duration,
            "completed_at": datetime.now().isoformat(),
            "backup_file": EXTRACTED_DATA_FILE
        }
        with open(FINAL_SUMMARY_FILE, 'w') as f:
            json.dump(summary, f, indent=4)

        print("\n" + "-"*50, flush=True)
        print("GRAPH BUILDING SUMMARY", flush=True)
        print("-"*50, flush=True)
        print(f"Batches Processed      : {total_batches}", flush=True)
        print(f"Total Relations Added  : {total_relations}", flush=True)
        print(f"Total Time Taken       : {duration:.2f} seconds", flush=True)
        print(f"Speed                  : {duration/total_batches:.2f} sec/batch", flush=True)
        print(f"📄 Full Data Backup    : {EXTRACTED_DATA_FILE}", flush=True)
        print("\n✅ Step 4 complete.", flush=True)
        print("💡 Open Neo4j Browser (http://localhost:7474) to visualize.", flush=True)

if __name__ == "__main__":
    run_step4()