# step6_scenario_generator.py
# STEP 6 — STRATEGIC SCENARIO GENERATION (The Final Report)

import json
import os
import sys

# ─────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────
try:
    from llama_cpp import Llama
except ImportError:
    print("❌ ERROR: Missing library.")
    print("Run: pip install llama-cpp-python")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
MODEL_PATH = "/home/anand/Downloads/Qwen3.5-4B-Q4_K_M.gguf"
INPUT_FILE = "output/step5_lens_analysis.json"
OUTPUT_FILE = "output/final_strategic_report.json"

# ─────────────────────────────────────────────
# ROBUST LLM CLIENT (Reused for stability)
# ─────────────────────────────────────────────

class LLMClient:
    def __init__(self, model_path, n_ctx=8192, n_threads=8, n_gpu_layers=-1):
        print(f"🔄 Initializing Strategist LLM...")
        self.model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        print("✅ Strategist Ready.")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            response = self.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4, # Slightly higher for creative scenario writing
                max_tokens=2048
            )
            
            content = response['choices'][0]['message']['content'].strip()
            
            # Cleanup Markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"⚠️ Generation Error: {e}")
            # Fallback raw text structure
            return {"error": str(e), "raw_content": content if 'content' in locals() else "Unknown"}

# ─────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────

def run_step6():
    print("\n" + "="*60)
    print("STEP 6 — GENERATING FINAL STRATEGIC SCENARIOS")
    print("="*60)

    # 1. Load Lens Analysis
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found. Run Step 5 first.")
        return

    with open(INPUT_FILE, "r") as f:
        lens_data = json.load(f)

    print(f"📂 Loaded {len(lens_data)} lens analyses.")
    
    # 2. Construct Context for the LLM
    # We concatenate the summaries and key insights into one big text
    context_builder = []
    for lens_name, data in lens_data.items():
        if "error" in data: continue # Skip failed lenses
        
        section = f"""
        --- {lens_name.upper()} LENS ---
        Risk Level: {data.get('risk_level', 'Unknown')}
        Summary: {data.get('summary', 'N/A')}
        Key Insight: {data.get('key_insight', 'N/A')}
        """
        context_builder.append(section)
    
    full_context = "\n".join(context_builder)

    # 3. Define the Final Prompt
    system_prompt = "You are a Senior Geopolitical and Financial Strategist. You are writing a confidential report for a high-stakes decision maker."
    
    user_prompt = f"""
    Based on the analysis from 7 different expert lenses provided below, generate a Strategic Scenario Report.

    EXPERT ANALYSIS INPUT:
    {full_context}

    INSTRUCTIONS:
    Your task is to synthesize these conflicting and agreeing viewpoints into a coherent report.
    1. Past Reconstruction: Briefly explain the chain of events that led to the current state.
    2. Current State: Describe the immediate reality and the dominant force (e.g., Panic, Greed, Stagnation).
    3. Future Scenarios: Generate 3 distinct scenarios:
       - Scenario A (Status Quo): What happens if no intervention occurs? (Most likely drift).
       - Scenario B (Intervention): What happens if key players act effectively? (Best case).
       - Scenario C (Black Swan): What is the worst-case low-probability, high-impact event?
    4. Early Warning Signals: List 3 specific data points to watch for to distinguish between these scenarios.

    Return the response in this JSON format:
    {{
        "event_topic": "Name of the event",
        "past_reconstruction": "string",
        "current_state": "string",
        "scenario_a": {{
            "name": "Status Quo",
            "description": "string",
            "probability": "High/Medium/Low"
        }},
        "scenario_b": {{
            "name": "Positive Intervention",
            "description": "string",
            "probability": "High/Medium/Low"
        }},
        "scenario_c": {{
            "name": "Black Swan",
            "description": "string",
            "probability": "High/Medium/Low"
        }},
        "early_warning_signals": ["signal 1", "signal 2", "signal 3"]
    }}
    """

    # 4. Execute Generation
    print("🧠 Synthesizing strategic scenarios...")
    strategist = LLMClient(MODEL_PATH, n_threads=8, n_gpu_layers=-1)
    
    final_report = strategist.generate_json(system_prompt, user_prompt)

    # 5. Save Output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_report, f, indent=4)

    print("\n" + "-"*60)
    print("STRATEGIC REPORT GENERATED")
    print("-"*60)
    print(f"📁 Saved to: {OUTPUT_FILE}")
    
    # Print a summary to console
    if "scenario_a" in final_report:
        print("\n📊 SCENARIO A (Status Quo):")
        print(f"   {final_report['scenario_a']['description'][:150]}...")
        print("\n📊 SCENARIO B (Intervention):")
        print(f"   {final_report['scenario_b']['description'][:150]}...")
        print("\n📊 SCENARIO C (Black Swan):")
        print(f"   {final_report['scenario_c']['description'][:150]}...")

    print("\n✅ Pipeline Complete. You have reached the end of the implementation roadmap.")

if __name__ == "__main__":
    run_step6()