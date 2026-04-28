# step1_filter.py
# STEP 1 — ENHANCED FILTERING (No External Parameters Required)

import json
import os
import re
from collections import Counter
from difflib import SequenceMatcher

# ─────────────────────────────────────────────
# BUILT-IN CONFIGURATION (No config.py needed)
# ─────────────────────────────────────────────

# File Paths
INPUT_FILE = "/home/anand/Videos/multiverse_insights_2.0/new_steps/raw_reddit.json"       # Change this if your input file has a different name
OUTPUT_DIR = "output"
OUTPUT_FILE = "step1_filtered.json"

# ─────────────────────────────────────────────
# CONFIGURATION FOR NICHE TOPICS (RESEARCH MODE)
# ─────────────────────────────────────────────

# Metadata Thresholds (RELAXED)
POST_MIN_ACCOUNT_AGE_DAYS = 1       # Allow new accounts (people make accounts to post news)
POST_MIN_COMMENT_KARMA = -1000     # Disable karma check (ignore negative karma)
POST_MIN_SCORE = 1                 # Keep almost all posts that have text
POST_MIN_WORDS = 15                # Keep short posts too

COMMENT_MIN_ACCOUNT_AGE_DAYS = 1   # Allow new users
COMMENT_MIN_COMMENT_KARMA = -1000  # Disable karma check
COMMENT_MIN_UPVOTE_RATIO = 0.0     # DISABLE THIS CHECK. It is the main killer.
COMMENT_MIN_SCORE = -10            # Allow downvoted comments (controversy is data!)
COMMENT_MIN_WORDS = 5              # Keep short comments
COMMENT_MAX_DEPTH = 10             # Allow deep comment threads

# Text Quality Thresholds (STRICT - This removes the noise)
MIN_UNIQUE_WORDS_RATIO = 0.3       # Keep this
MAX_CAPS_RATIO = 0.5               # Loosen slightly (allow excitement)
MAX_EMOJI_COUNT = 5                # STRICT (remove spam)
MAX_PUNCTUATION_RATIO = 0.3        # Keep this
MIN_AVG_WORD_LENGTH = 2.5          # Loosen slightly
MAX_REPEAT_WORD_RATIO = 0.3        # Loosen slightly

# Spam/Link Detection (STRICT)
MAX_URL_COUNT = 2                  # STRICTER (remove link spammers)
BLOCKED_URL_PATTERNS = ["bit.ly", "t.co", "tinyurl", "linktr.ee"]
BLOCKED_KEYWORDS = ["subscribe", "follow me", "check out my", "buy now", "free money"]

# Deduplication
SIMILARITY_THRESHOLD = 0.85

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def word_count(text: str) -> int:
    if not text or not isinstance(text, str):
        return 0
    return len(text.strip().split())

def extract_urls(text: str) -> list:
    url_pattern = r'https?://\S+|www\.\S+'
    return re.findall(url_pattern, text.lower())

def extract_emojis(text: str) -> list:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.findall(text)

def calculate_text_quality(text: str) -> tuple[bool, str]:
    if not text or not isinstance(text, str):
        return False, "empty_text"
    
    text_clean = text.strip()
    if text_clean.lower() in ["[removed]", "[deleted]", ""]:
        return False, "removed_or_deleted"
    
    words = text_clean.split()
    word_count_len = len(words)
    
    if word_count_len == 0:
        return False, "no_words"
    
    unique_words = set(w.lower() for w in words if len(w) > 2)
    if unique_words and (len(unique_words) / word_count_len) < MIN_UNIQUE_WORDS_RATIO:
        return False, "low_unique_words"
    
    alpha_chars = [c for c in text_clean if c.isalpha()]
    if alpha_chars:
        caps_ratio = len([c for c in alpha_chars if c.isupper()]) / len(alpha_chars)
        if caps_ratio > MAX_CAPS_RATIO:
            return False, "too_much_caps"
    
    if len(extract_emojis(text_clean)) > MAX_EMOJI_COUNT:
        return False, "too_many_emojis"
    
    punct_chars = [c for c in text_clean if c in "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"]
    if word_count_len > 0 and (len(punct_chars) / len(text_clean)) > MAX_PUNCTUATION_RATIO:
        return False, "too_much_punctuation"
    
    avg_word_len = sum(len(w) for w in words) / word_count_len
    if avg_word_len < MIN_AVG_WORD_LENGTH:
        return False, "too_short_words"
    
    if len(words) > 5:
        word_freq = Counter(w.lower() for w in words if len(w) > 2)
        most_common_count = word_freq.most_common(1)[0][1]
        if (most_common_count / word_count_len) > MAX_REPEAT_WORD_RATIO:
            return False, "too_repetitive"
    
    return True, "ok"

def check_spam_patterns(text: str) -> tuple[bool, str]:
    text_lower = text.lower()
    urls = extract_urls(text)
    if len(urls) > MAX_URL_COUNT:
        return False, "too_many_urls"
    for blocked in BLOCKED_URL_PATTERNS:
        if blocked in text_lower:
            return False, "blocked_url_pattern"
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return False, "spam_keyword"
    return True, "ok"

def is_quality_text(text: str) -> tuple[bool, str]:
    valid, reason = calculate_text_quality(text)
    if not valid: return False, reason
    valid, reason = check_spam_patterns(text)
    if not valid: return False, reason
    return True, "ok"

def calculate_similarity(text1: str, text2: str) -> float:
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

class Deduplicator:
    def __init__(self, threshold: float = 0.85):
        self.seen_texts = []
        self.threshold = threshold
    
    def is_duplicate(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if text_lower in self.seen_texts:
            return True
        for seen in self.seen_texts[-100:]:
            if calculate_similarity(text_lower, seen) > self.threshold:
                return True
        self.seen_texts.append(text_lower)
        return False


# ─────────────────────────────────────────────
# VALIDATION FUNCTIONS
# ─────────────────────────────────────────────

def is_valid_post(post: dict, dedup: Deduplicator = None) -> tuple[bool, str]:
    if post.get("author_account_age_days", 0) < POST_MIN_ACCOUNT_AGE_DAYS:
        return False, "low_account_age"
    if post.get("author_comment_karma", 0) < POST_MIN_COMMENT_KARMA:
        return False, "low_karma"
    if post.get("score", 0) < POST_MIN_SCORE:
        return False, "low_score"
    if word_count(post.get("selftext", "")) < POST_MIN_WORDS:
        return False, "too_few_words"
    
    selftext = post.get("selftext", "")
    valid, reason = is_quality_text(selftext)
    if not valid: return False, f"content_quality: {reason}"
    
    if dedup and dedup.is_duplicate(selftext):
        return False, "duplicate_post"
    return True, "ok"

# def is_valid_comment(comment: dict, depth: int, dedup: Deduplicator = None) -> tuple[bool, str]:
#     if depth > COMMENT_MAX_DEPTH: return False, "max_depth_exceeded"
#     if comment.get("author_account_age_days", 0) < COMMENT_MIN_ACCOUNT_AGE_DAYS: return False, "low_account_age"
#     if comment.get("author_comment_karma", 0) < COMMENT_MIN_COMMENT_KARMA: return False, "low_karma"
#     if comment.get("upvote_ratio", 0) < COMMENT_MIN_UPVOTE_RATIO: return False, "low_upvote_ratio"
#     if comment.get("score", 0) < COMMENT_MIN_SCORE: return False, "low_score"
#     if word_count(comment.get("body", "")) < COMMENT_MIN_WORDS: return False, "too_few_words"
    
#     body = comment.get("body", "")
#     valid, reason = is_quality_text(body)
#     if not valid: return False, f"content_quality: {reason}"
    
#     if dedup and depth == 0 and dedup.is_duplicate(body):
#         return False, "duplicate_comment"
#     return True, "ok"


def is_valid_comment(comment: dict, depth: int, dedup: Deduplicator = None) -> tuple[bool, str]:
    if depth > COMMENT_MAX_DEPTH: return False, "max_depth_exceeded"
    
    # RELAXED: Ignore account age for niche topics
    # if comment.get("author_account_age_days", 0) < COMMENT_MIN_ACCOUNT_AGE_DAYS: return False, "low_account_age"
    
    # RELAXED: Ignore karma
    # if comment.get("author_comment_karma", 0) < COMMENT_MIN_COMMENT_KARMA: return False, "low_karma"
    
    # CRITICAL FIX: Handle missing ratio
    upvote_ratio = comment.get("upvote_ratio")
    # Only fail if ratio is explicitly provided and fails the threshold.
    # If ratio is None (missing), we PASS it.
    if upvote_ratio is not None and upvote_ratio < COMMENT_MIN_UPVOTE_RATIO:
        return False, "low_upvote_ratio"
        
    # RELAXED: Allow low scores
    # if comment.get("score", 0) < COMMENT_MIN_SCORE: return False, "low_score"
    
    if word_count(comment.get("body", "")) < COMMENT_MIN_WORDS: return False, "too_few_words"
    
    body = comment.get("body", "")
    valid, reason = is_quality_text(body)
    if not valid: return False, f"content_quality: {reason}"
    
    if dedup and depth == 0 and dedup.is_duplicate(body):
        return False, "duplicate_comment"
    return True, "ok"
def filter_replies(replies: list, depth: int, dedup: Deduplicator = None) -> list:
    if not replies: return []
    filtered = []
    for reply in replies:
        valid, _ = is_valid_comment(reply, depth, dedup)
        if valid:
            reply_copy = dict(reply)
            if "replies" in reply_copy:
                reply_copy["replies"] = filter_replies(reply_copy["replies"], depth + 1, dedup)
            filtered.append(reply_copy)
    return filtered

def filter_comments(comments: list, dedup: Deduplicator = None) -> list:
    if not comments: return []
    filtered = []
    for comment in comments:
    
        valid, _ = is_valid_comment(comment, depth=0, dedup=dedup)
        if valid:
            comment_copy = dict(comment)
            if "replies" in comment_copy:
                comment_copy["replies"] = filter_replies(comment_copy["replies"], 1, dedup)
            filtered.append(comment_copy)
    return filtered


# ─────────────────────────────────────────────
# MAIN FILTER FUNCTION
# ─────────────────────────────────────────────

def run_filter(input_path: str, output_path: str) -> dict:
    print("\n" + "="*50)
    print("STEP 1 — ENHANCED FILTERING")
    print("="*50)
    
    dedup = Deduplicator(threshold=SIMILARITY_THRESHOLD)

    print(f"\n📂 Loading: {input_path}")
    with open(input_path, "r") as f:
        raw_data = json.load(f)
    print(f"   Loaded {len(raw_data)} posts")

    stats = {
        "original_posts": len(raw_data), "kept_posts": 0, "rejected_posts": 0,
        "original_comments": 0, "kept_comments": 0, "rejected_comments": 0,
        "rejection_reasons": {}
    }

    filtered_posts = []

    for post in raw_data:
        original_comments = len(post.get("comments", []))
        stats["original_comments"] += original_comments

        valid, reason = is_valid_post(post, dedup)

        if not valid:
            stats["rejected_posts"] += 1
            stats["rejected_comments"] += original_comments
            stats["rejection_reasons"][reason] = stats["rejection_reasons"].get(reason, 0) + 1
            continue

        filtered_comments = filter_comments(post.get("comments", []), dedup)
        kept_comments = len(filtered_comments)
        
        stats["kept_comments"] += kept_comments
        stats["rejected_comments"] += (original_comments - kept_comments)

        post_copy = dict(post)
        post_copy["comments"] = filtered_comments
        post_copy["_filter_stats"] = {"original_comments": original_comments, "kept_comments": kept_comments}
        
        filtered_posts.append(post_copy)
        stats["kept_posts"] += 1

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(filtered_posts, f, indent=2)

    print("\n" + "-"*50)
    print("FILTERING SUMMARY")
    print("-"*50)
    print(f"Posts    : {stats['original_posts']} -> {stats['kept_posts']} kept ({stats['rejected_posts']} rejected)")
    print(f"Comments : {stats['original_comments']} -> {stats['kept_comments']} kept ({stats['rejected_comments']} rejected)")
    print(f"\n📁 Output saved: {output_path}")

    if stats["rejection_reasons"]:
        print("\nRejection reasons:")
        for reason, count in sorted(stats["rejection_reasons"].items(), key=lambda x: -x[1]):
            print(f"   - {reason}: {count}x")

    return stats


# ─────────────────────────────────────────────
# ENTRY POINT (Zero Parameters Needed)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Automatically figures out where this script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Defines input and output automatically
    input_file = os.path.join(base_dir, INPUT_FILE)
    output_file = os.path.join(base_dir, OUTPUT_DIR, OUTPUT_FILE)
    
    # Check if input file exists before running
    if not os.path.exists(input_file):
        print(f"❌ ERROR: Could not find input file '{INPUT_FILE}' in {base_dir}")
        print("Please put your raw Reddit JSON file in the same folder and name it 'raw_data.json'")
    else:
        run_filter(input_file, output_file)
        print("\n✅ Step 1 complete.\n")