# step2_batching.py
# STEP 2 — OPTIMIZED 16k TOKEN BATCHING (Bin Packing Algorithm)

import json
import os
import sys

try:
    import tiktoken
except ImportError:
    print("❌ ERROR: 'tiktoken' is required. Run: pip install tiktoken")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
INPUT_FILE = "output/step1_filtered.json"
OUTPUT_DIR = "output"
OUTPUT_FILE = "step2_batched.json"

MAX_BATCH_TOKENS = 16000  # 16k token limit
ENCODING_MODEL = "cl100k_base"  # Standard for GPT-4 / modern LLMs


# ─────────────────────────────────────────────
# TOKEN LOGIC
# ─────────────────────────────────────────────

def get_encoder():
    """Load the tokenizer."""
    try:
        return tiktoken.get_encoding(ENCODING_MODEL)
    except Exception:
        return tiktoken.encoding_for_model("gpt-4")

def count_tokens(item: dict, encoder) -> int:
    """Calculate exact tokens for a dictionary by converting to JSON string."""
    json_str = json.dumps(item, ensure_ascii=False, indent=2)
    tokens = encoder.encode(json_str)
    return len(tokens)


# ─────────────────────────────────────────────
# OPTIMIZED BATCHING ENGINE (Best Fit Decreasing)
# ─────────────────────────────────────────────

def create_optimized_batches(posts: list, encoder) -> list:
    """
    Uses Bin Packing (Best Fit Decreasing) to minimize total batches
    and maximize the 16k token window usage.
    """
    print("   ⏳ Step 1/3: Calculating tokens for all posts...")
    tokenized_posts = []
    skipped_posts = 0
    
    for i, post in enumerate(posts):
        post_id = post.get("post_id", f"index_{i}")
        tokens = count_tokens(post, encoder)
        
        # Skip posts that are larger than the entire window
        if tokens > MAX_BATCH_TOKENS:
            print(f"   ⚠️  Skipping {post_id}: {tokens} tokens (Exceeds 16k alone)")
            skipped_posts += 1
        else:
            tokenized_posts.append({'tokens': tokens, 'data': post})

    print(f"   ⏳ Step 2/3: Sorting posts by size (Largest → Smallest)...")
    # Sort descending by token count (Crucial for Bin Packing efficiency)
    tokenized_posts.sort(key=lambda x: x['tokens'], reverse=True)

    print(f"   ⏳ Step 3/3: Packing into batches (Best Fit Algorithm)...\n")
    
    # Bins represent our batches. Each bin tracks remaining space.
    bins = [] 

    for item in tokenized_posts:
        tokens = item['tokens']
        post_data = item['data']
        post_id = post_data.get("post_id", "?")
        
        best_bin_idx = -1
        min_remaining_space = float('inf')

        # Find the tightest fitting batch
        for i, b in enumerate(bins):
            if b['remaining'] >= tokens:
                space_left_after_fit = b['remaining'] - tokens
                # We want the batch that will have the LEAST space left after adding this
                if space_left_after_fit < min_remaining_space:
                    min_remaining_space = space_left_after_fit
                    best_bin_idx = i

        if best_bin_idx != -1:
            # Found a batch that fits perfectly
            bins[best_bin_idx]['remaining'] -= tokens
            bins[best_bin_idx]['posts'].append(post_data)
            print(f"   ✅ Added {post_id} ({tokens} tok) → Batch {best_bin_idx + 1} (Space left: {bins[best_bin_idx]['remaining']})")
        else:
            # Didn't fit anywhere, create a new batch
            bins.append({
                'remaining': MAX_BATCH_TOKENS - tokens,
                'posts': [post_data]
            })
            print(f"   🆕 Created Batch {len(bins)} with {post_id} ({tokens} tok) (Space left: {MAX_BATCH_TOKENS - tokens})")

    # Format for final JSON output
    output_batches = []
    for i, b in enumerate(bins):
        output_batches.append({
            "batch_index": i + 1,
            "total_tokens": MAX_BATCH_TOKENS - b['remaining'],
            "post_count": len(b['posts']),
            "posts": b['posts']
        })

    return output_batches, skipped_posts


# ─────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────

def run_batching(input_path: str, output_path: str):
    print("\n" + "="*50)
    print("STEP 2 — OPTIMIZED BIN-PACKING BATCHING")
    print("="*50)

    if not os.path.exists(input_path):
        print(f"❌ Error: Could not find {input_path}. Run step1_filter.py first.")
        return

    print(f"\n📂 Loading: {input_path}")
    with open(input_path, "r") as f:
        posts = json.load(f)
    
    print(f"   Loaded {len(posts)} posts")
    
    encoder = get_encoder()
    print(f"   Tokenizer loaded: {ENCODING_MODEL}\n")

    batches, skipped = create_optimized_batches(posts, encoder)

    # Calculate final stats
    total_tokens_all = sum(b["total_tokens"] for b in batches)
    avg_utilization = (total_tokens_all / (len(batches) * MAX_BATCH_TOKENS)) * 100 if batches else 0
    
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(batches, f, indent=2)

    # Print Summary
    print("\n" + "-"*50)
    print("BATCHING SUMMARY")
    print("-"*50)
    print(f"Total Posts Processed  : {len(posts)}")
    print(f"Posts Skipped (>16k)   : {skipped}")
    print(f"Total Batches Created  : {len(batches)} ⬇️ (Minimized via Algorithm)")
    print(f"Total Tokens Packaged  : {total_tokens_all:,}")
    print(f"Context Window Usage   : {avg_utilization:.1f}% average utilization")
    
    print("\nBatch Breakdown:")
    for b in batches:
        utilization = (b['total_tokens'] / MAX_BATCH_TOKENS) * 100
        print(f"   Batch {b['batch_index']}: {b['post_count']} posts | {b['total_tokens']:,} tokens ({utilization:.1f}% full)")

    print(f"\n📁 Output saved: {output_path}")
    print("✅ Step 2 complete.\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    input_file = os.path.join(base_dir, INPUT_FILE)
    output_file = os.path.join(base_dir, OUTPUT_DIR, OUTPUT_FILE)
    
    run_batching(input_file, output_file)