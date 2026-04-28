# step3_compress.py
# STEP 3 — TOKEN COMPRESSION (JSON to Structured Text)

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
INPUT_FILE = "output/step2_batched.json"
OUTPUT_DIR = "output"
OUTPUT_FILE = "step3_llm_ready.json"

ENCODING_MODEL = "cl100k_base"


# ─────────────────────────────────────────────
# TEXT FORMATTER (The Token Saver)
# ─────────────────────────────────────────────

def format_comment(comment: dict, depth: int = 0) -> str:
    """Recursively format a comment into lightweight text."""
    indent = "  " * depth  # Visual indentation for replies
    lines = [
        f"{indent}[COMMENT]",
        f"{indent}Author: {comment.get('author', 'N/A')}",
        f"{indent}Score: {comment.get('score', 0)}",
        f"{indent}Body: {comment.get('body', '')}"
    ]
    
    # Handle nested replies
    replies = comment.get('replies', [])
    if replies:
        for reply in replies:
            lines.append(format_comment(reply, depth + 1))
            
    lines.append(f"{indent}[/COMMENT]")
    return "\n".join(lines)


def format_post_to_text(post: dict) -> str:
    """Convert a single post dictionary into highly compressed text."""
    lines = [
        "[POST]",
        f"ID: {post.get('post_id', 'N/A')}",
        f"Author: {post.get('author', 'N/A')}",
        f"Title: {post.get('title', 'N/A')}",
        f"Score: {post.get('score', 0)}",
        f"Body: {post.get('selftext', '')}"
    ]
    
    comments = post.get('comments', [])
    if comments:
        lines.append("[COMMENTS]")
        for c in comments:
            lines.append(format_comment(c, depth=0))
        lines.append("[/COMMENTS]")
        
    lines.append("[/POST]\n") # Extra space between posts
    return "\n".join(lines)


# ─────────────────────────────────────────────
# MAIN COMPRESSION FUNCTION
# ─────────────────────────────────────────────

def run_compression(input,output):
    print("\n" + "="*50)
    print("STEP 3 — TOKEN COMPRESSION")
    print("="*50)
    input_path = input 
    output_path = output

    if not os.path.exists(input_path):
        print(f"❌ Error: Could not find {input_path}. Run previous steps first.")
        return

    print(f"\n📂 Loading: {input_path}")
    with open(input_path, "r") as f:
        batches = json.load(f)
    
    encoder = tiktoken.get_encoding(ENCODING_MODEL)
    
    final_batches = []
    total_original_tokens = 0
    total_compressed_tokens = 0

    print(f"🔧 Compressing {len(batches)} batches...\n")

    for batch in batches:
        batch_text_parts = []
        
        for post in batch["posts"]:
            # Convert post to text format
            batch_text_parts.append(format_post_to_text(post))
        
        # Combine all posts in this batch into one massive string
        compressed_text = "\n".join(batch_text_parts)
        
        # Count tokens of the NEW text format
        compressed_tokens = len(encoder.encode(compressed_text))
        original_tokens = batch["total_tokens"]
        
        total_original_tokens += original_tokens
        total_compressed_tokens += compressed_tokens
        
        # Calculate savings
        saved_tokens = original_tokens - compressed_tokens
        savings_percent = (saved_tokens / original_tokens) * 100 if original_tokens > 0 else 0

        print(f"📦 Batch {batch['batch_index']}: {original_tokens:,} → {compressed_tokens:,} tokens (Saved {saved_tokens:,} tokens / {savings_percent:.1f}%)")

        # Store in our final output format
        final_batches.append({
            "batch_index": batch["batch_index"],
            "post_count": batch["post_count"],
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "text_for_llm": compressed_text  # <-- THIS IS WHAT YOU SEND TO THE API
        })

    # Save the compressed file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_batches, f, indent=2)

    # Final Summary
    total_saved = total_original_tokens - total_compressed_tokens
    overall_savings = (total_saved / total_original_tokens) * 100 if total_original_tokens > 0 else 0

    print("\n" + "-"*50)
    print("COMPRESSION SUMMARY")
    print("-"*50)
    print(f"Total Original Tokens   : {total_original_tokens:,}")
    print(f"Total Compressed Tokens : {total_compressed_tokens:,}")
    print(f"💰 TOTAL TOKENS SAVED   : {total_saved:,} ({overall_savings:.1f}% reduction)")
    print(f"\n📁 Output saved: {output_path}")
    print("\n💡 HOW TO USE: Extract the 'text_for_llm' string from this JSON and pass it directly to your LLM API.")
    print("✅ Step 3 complete.\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    input_file = os.path.join(base_dir, INPUT_FILE)
    output_file = os.path.join(base_dir, OUTPUT_DIR, OUTPUT_FILE)
    
    run_compression(input_file, output_file)