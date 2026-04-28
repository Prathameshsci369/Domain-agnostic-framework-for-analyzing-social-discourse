import os
import sys
import time
import logging
from functools import wraps
import json

# ─────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────
log_file = "pipeline_execution.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# RETRY DECORATOR
# ─────────────────────────────────────────────
def retry_pipeline_step(max_retries=3, delay=5):
    """
    Decorator to retry a specific step if it fails.
    Useful for DB connections or LLM timeouts.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    logger.info(f"▶️  Starting: {func.__name__}")
                    result = func(*args, **kwargs)
                    logger.info(f"✅ Success: {func.__name__}")
                    return result
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"❌ Step {func.__name__} failed after {max_retries} retries.")
                        raise e
                    logger.warning(f"⚠️  Step {func.__name__} failed (Attempt {retries}/{max_retries}). Retrying in {delay}s... Error: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

# ─────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────
# Importing the main functions from the other files.
# Note: Step 4, 5, and 6 require small edits (see below) to accept arguments.

from step1_filter import run_filter
from step2_batching import run_batching
from step3_compress import run_compression

# We import the renamed main functions from the modified files
from step4_extract_graph import run_step4
from step5_final_graph_synthesis import run_step5
from step6_scenario_generator import run_step6

# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    logger.info("="*60)
    logger.info("STARTING REDDIT INSIGHTS PIPELINE")
    logger.info("="*60)

    # 1. Define Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "output")
    
    # Input Data
    input_raw = "/home/anand/Videos/multiverse_insights_2.0/new_steps/raw_reddit.json" # Your raw data
    
    # Intermediate Files
    step1_out = os.path.join(output_dir, "step1_filtered.json")
    step2_out = os.path.join(output_dir, "step2_batched.json")
    step3_out = os.path.join(output_dir, "step3_llm_ready.json")
    # Step 4, 5, 6 handle their own internal outputs, but we pass inputs to them
    
    # 2. Check Input
    if not os.path.exists(input_raw):
        logger.error(f"Input file not found: {input_raw}")
        return

    try:
        # --- STEP 1: FILTER ---
        # Already accepts (input, output)
        @retry_pipeline_step(max_retries=2)
        def execute_step1():
            return run_filter(input_raw, step1_out)
        execute_step1()

        # --- STEP 2: BATCHING ---
        # Already accepts (input, output)
        @retry_pipeline_step(max_retries=2)
        def execute_step2():
            return run_batching(step1_out, step2_out)
        execute_step2()

        # --- STEP 3: COMPRESSION ---
        # Already accepts (input, output)
        @retry_pipeline_step(max_retries=2)
        def execute_step3():
            return run_compression(step2_out, step3_out)
        execute_step3()

        # --- STEP 4: GRAPH BUILDING ---
        # Needs modification to accept input path
        @retry_pipeline_step(max_retries=3) # Higher retry for DB ops
        def execute_step4():
            # We pass the input path. Output is handled internally or returned.
            return run_step4(step3_out)
        execute_step4()

        # --- STEP 5: LENS ANALYSIS ---
        # Needs modification to accept input path
        @retry_pipeline_step(max_retries=3)
        def execute_step5():
            # Assuming step5 generates output/step5_lens_analysis.json internally
            return run_step5()
        execute_step5()

        # --- STEP 6: FINAL REPORT ---
        # Needs modification to accept input/output paths
        @retry_pipeline_step(max_retries=3)
        def execute_step6():
            # Assuming step6 reads from step5 output
            step5_input = os.path.join(output_dir, "step5_lens_analysis.json")
            final_output = os.path.join(output_dir, "final_strategic_report.json")
            return run_step6(step5_input, final_output)
        
        final_result_path = execute_step6()

        # 3. Render Dashboard Output (Step 6 Output)
        logger.info("-" * 60)
        logger.info("PIPELINE COMPLETE. RENDERING DASHBOARD DATA...")
        logger.info("-" * 60)
        
        if os.path.exists(final_result_path):
            with open(final_result_path, 'r') as f:
                dashboard_data = json.load(f)
            
            # This is the output ready for your dashboard
            print("\n📊 DASHBOARD PAYLOAD (Step 6 Output):")
            print(json.dumps(dashboard_data, indent=4))
            
            logger.info(f"✅ Dashboard data generated from: {final_result_path}")
        else:
            logger.warning("Final report file not found.")

    except Exception as e:
        logger.critical(f"🔥 Pipeline crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()