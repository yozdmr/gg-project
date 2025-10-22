import json
import re
import argparse
from datetime import datetime
from typing import Iterable, Iterator, Dict, Any, Optional


USE_LANGDETECT = True # a switch to disable language detection entirely when not using

try:
    from ftfy import fix_text
except Exception:
    def fix_text(s): return s

try:
    import unidecode
    def to_ascii(s): return unidecode.unidecode(s)
except Exception:
# Fallback: if unidecode is not installed, return the string unchanged
    def to_ascii(s): return s

try:
    from langdetect import detect_langs
except Exception:
# If langdetect is missing, disable language detection
    detect_langs = None

# regular expression
URL_RE = re.compile(r'https?://\S+')
MENTION_RE = re.compile(r'@(\w+)')
HASHTAG_RE = re.compile(r'#(\w+)')

# common English hints for a quick heuristic
EN_HINTS_RE = re.compile(
    r'\b(the|and|is|are|was|were|you|i|he|she|we|they|this|that|of|to|in|for|on|with|best|win|wins|golden|globe|globes)\b',
    re.IGNORECASE
)

# check to avoid fixing on already-ASCII text
def _is_mostly_ascii(s: str, threshold: float = 0.98) -> bool:
    if not s:
        return True
    ascii_count = sum(1 for ch in s if ord(ch) < 128)
    return (ascii_count / len(s)) >= threshold

def basic_clean(text: str) -> str:
    """
    Basic cleaning pipeline:
    1)fix encoding (HTML entities / mojibake) 2)unify characters 3) remove URL 4)collapse repeated whitespaces
    """
    if not text:
        return ""
    # run ftfy/unidecode only if needed (non-ASCII or contains HTML entities)
    t = text
    if not _is_mostly_ascii(t) or "&" in t:
        t = fix_text(t)              # fix HTML entity/garbled bytes
        t = to_ascii(t)              # transfer to ASCII
    t = URL_RE.sub(" ", t)           # remove URL
    t = " ".join(t.split())          # collapse whitespace
    return t

def strip_tags(text: str) -> str:
    """
    remove @/# but keep the token bodies for lanaguage detection and rule matching(slides 33-36, 40-41)
    e.g. @BenAffleck -> BenAffleck; #BestDirector -> BestDirector
    """
    t = re.sub(r'@(\w+)', r'\1', text)
    t = re.sub(r'#(\w+)', r'\1', t)
    t = " ".join(t.split())
    return t

def find_mentions_hashtags(text: str):
    """Return lists of @mentions and #hashtags from the given text."""
    mentions = MENTION_RE.findall(text)
    hashtags = HASHTAG_RE.findall(text)
    return mentions, hashtags

def detect_language(text_no_tags: str, min_conf: float = 0.8):

    """
    Language detection method, use confidence of language detectors (slides 30)
    - Run on text without @/# for better accuracy.
    - If top probability >= min_conf (0.8 here), choose to keep, otherwise discard.
    - If langdetect is not available or text is empty, return ('unk', 0.0).
    """
    #allow turning detection off completely 
    if not USE_LANGDETECT:
        return ("unk", 0.0)

    t = text_no_tags
    if not t.strip():
        return ("unk", 0.0)

    # heuristic gate before calling langdetect
    # 1) Mostly-ASCII + has common English words -> treat as English
    if _is_mostly_ascii(t) and EN_HINTS_RE.search(t):
        return ("en", 0.95)
    # 2) Very non-ASCII -> likely not English; skip the slow detector
    ascii_ratio = sum(1 for ch in t if ord(ch) < 128) / max(len(t), 1)
    if ascii_ratio <= 0.50:
        return ("unk", 0.50)

    # Fallback to the original detector only for ambiguous ones
    if (detect_langs is None):
        return ("unk", 0.0)
    try:
        cand = detect_langs(t)  # e.g.[en:0.99, ...]
        if not cand:
            return ("unk", 0.0)
        top = cand[0]
        lang = str(top.lang)
        conf = float(top.prob)
        if conf < min_conf:
            return ("unk", conf)
        return (lang, conf)
    except Exception:
        return ("unk", 0.0)

def split_rt_qt(text: str):
    """
    Detect two most common Twitter patterns: (slides 42-45)
      - RT: retweet starting with 'RT @user: ...'
      - QT: quote-tweet containing ' RT @user: ...' later in the string
    Returns:
      (is_rt, is_qt, rt_user, rt_text, qt_user, qt_text, added_text)
    """
    # RT at the very beginning
    if text.startswith("RT @"):
        m = re.match(r'^RT @(\w+):\s*(.*)$', text)
        if m:
            return True, False, m.group(1), m.group(2), None, None, None

    # QT somewehere like: ' ... RT @user: quoted ...'
    m = re.search(r'\sRT @(\w+):\s*(.*)$', text)
    if m:
        added_text = text[:m.start()].strip() # user's own comment before quote
        return False, True, None, None, m.group(1), m.group(2), added_text

    return False, False, None, None, None, None, None

def preprocess_one(tweet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input: original tweet dict (including at least 'text' and 'timestamp_ms').
    Output: a processed new dict with normalized text and useful extracted fields.
    """
    raw_text = tweet.get("text", "")
    clean = basic_clean(raw_text)
    mentions, hashtags = find_mentions_hashtags(clean)
    no_tags = strip_tags(clean)

    # parse RT/QT on cleaned text 
    is_rt, is_qt, rt_user, rt_text, qt_user, qt_text, added_text = split_rt_qt(clean)

    # language detection on text without @/# for better accuracy（slides 40–41）
    lang, lang_conf = detect_language(no_tags)

    # convert timestamp_ms to ISO string（slides 49–51）
    ts_ms = tweet.get("timestamp_ms")
    iso_time = None
    if ts_ms is not None:
        try:
            # beacuse sometimes maybe string
            ts_ms = int(ts_ms)
            iso_time = datetime.fromtimestamp(ts_ms / 1000).isoformat(sep=" ")
        except Exception:
            pass

    return {
        "id": tweet.get("id_str") or tweet.get("id"),
        "original_text": raw_text,
        "clean_text": clean,           # after encoding fix / URL removal / whitespace
        "text_no_tags": no_tags,       # remove #/@ but keep token bodies
        "mentions": mentions,          # ['BenAffleck', ...]
        "hashtags": hashtags,          # ['BestDirector', ...]
        "is_retweet": is_rt,
        "is_quote": is_qt,
        "rt_user": rt_user,
        "rt_text": rt_text,
        "qt_user": qt_user,
        "qt_text": qt_text,
        "qt_added_text": added_text,   # user's own comment in QT 
        "lang": lang,                  # 'en' / 'unk'
        "lang_conf": lang_conf,        # 0~1
        "timestamp_iso": iso_time,     # 'YYYY-MM-DD HH:MM:SS', e.g.'2013-01-13 19:58:11'
        "timestamp_ms": ts_ms,         #  original ms since epoch (int if parseable)
    }

def load_json(path: str):
    """
    load gg2013.json which is a json list
    If a dict is found, try to read the 'tweets' list key.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tweets", []) if isinstance(data, dict) else data

def preprocess_stream(tweets: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    for tw in tweets:
        yield preprocess_one(tw)

def preprocess_many(tweets: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return list(preprocess_stream(tweets))

def preprocess_file_to_jsonl(input_json: str, out_path: str) -> int:
    data = load_json(input_json)
    n = 0
    with open(out_path, "w", encoding="utf-8") as w:
        for rec in preprocess_stream(data):
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json", help="path to gg2013.json")
    ap.add_argument("--out", default="gg2013_preprocessed.jsonl",
                    help="output JSONL (one tweet per line)")
    args = ap.parse_args()

    n = preprocess_file_to_jsonl(args.input_json, args.out)
    print(f"Done. Wrote {n} lines to {args.out}")

if __name__ == "__main__":
    main()



