# Winner identification gives:
#   tweets: preprocessed records with fields like qt_text / rt_text / clean_text / text_no_tags / lang / lang_conf / timestamp_ms
#   award_names: official award strings to predict 
#   nominees_by_award: {award -> [nominees]}
#
# Approach:
#   1) language/time gate.
#   2) For each tweet, prefer factual-looking sentences (like "wins / goes to / is awarded to"). Use local windows around the verb to align award and candidate.
#   3) Award alignment: "X wins Y" vs "Y goes to X":
#      Match award names via token Jaccard + anchor tokens (e.g., drama/actor/television).
#   4) Candidate extraction:
#      work-type awards (Picture/Film/Series/Song/Score…): substring match against nominees
#      type awards
#   5) Vote per (award, candidate), de-duplicate per tweet, merge near duplicates.
#
# Notes:
#    it is driven by award_names + nominees_by_award + thresholds.


import re
from collections import defaultdict
from typing import Dict, List, Tuple, Iterable, Optional

#global thresholds 
AWARD_STOPWORDS = {
    "best","motion","picture","movie","performance","by","in","a","an","the","of","or","and"
}
#threshold
MIN_JACCARD = 0.4               
MIN_ANCHOR_OVERLAP = 2          
WEIGHT_QT, WEIGHT_RT, WEIGHT_RAW = 2, 2, 1  # quote/retweet/original weights for voting

# language / time gates 
ALLOWED_LANGS = {"en"}          # default English only here but can change to pass {"en","unk"}
LANG_MIN_CONF = 0.8             # minimal langdetect confidence 
TIME_WINDOW: Optional[Tuple[int, int]] = None  # (start_ms, end_ms) or None

# Regex
WIN_TRIGGERS = [
    r"\b(wins?|won|takes?|took|gets?|got|earns?|earned|secures?|secured|snags?|bag(?:s|ged)|picks?\s+up)\b",
    r"\b(award|globe)s?\s+(?:goes|went)\s+to\b",
    r"\b(?:is|was)\s+awarded\s+to\b",
    r"\b(?:goes|went)\s+to\b",
]

# exclude non-factual / predictive / meta speech (hope/should/if wins/etc.)
NON_FACTUAL_RE = re.compile(
 r"\b(hope|should|deserve[sd]?|wish|predict(?:ion|s)?|guess|"
 r"if\s+\w+\s+wins?|wins?\s+if|"
 r"nominee|nominated|noms?|present(?:ed|ing|s)|host(?:ed|ing|s))\b",
 re.IGNORECASE,
)

# verb use for "X wins Y" / "Y goes to X" local windows
WIN_VERB = re.compile(
    r"\b(wins?|won|takes?|took|gets?|got|earns?|earned|secures?|secured|snags?|bag(?:s|ged)|picks?\s+up|(?:goes|went)\s+to|is\s+awarded\s+to)\b",
    re.IGNORECASE,
)

# "Best …" phrase helps award matching
BEST_PHRASE = re.compile(r"\bBest\s+[A-Za-z][A-Za-z\s\-\&/]+", re.IGNORECASE)

# heuristic to decide which awards represent "works/titles" (film/series/song/score…)
TITLE_AWARD_HINT = re.compile(
    r"\b(Picture|Film|Series|Television|TV|Song|Score|Screenplay|Animated|Foreign)\b",
    re.IGNORECASE,
)

# Normalization & utilities
def normalize_award(s: str) -> str:
    """Light canonicalization for comparing award names (case/punct tolerant)."""
    s = (s or "").lower().replace("&", "and")
    s = re.sub(r"\bmini[-\s]*series\b", "miniseries", s)
    s = re.sub(r"\btv\b", "television", s)
    s = re.sub(r"[^a-z0-9\s-]", " ", s)  # keep hyphen
    return re.sub(r"\s+", " ", s).strip()

def award_anchors(name: str) -> set:
    """Extract anchor tokens from an award name (remove bland words)."""
    toks = normalize_award(name).split()
    return {t for t in toks if t not in AWARD_STOPWORDS}

def build_award_index(awards: List[str]) -> Dict[str, set]:
    """Precompute anchors per award for matching."""
    return {a: award_anchors(a) for a in awards}

def canon_person(s: str) -> str:
    """Normalize person names for merging (Title Case, drop mentions/punct)."""
    s = re.sub(r"[@#]\w+", " ", s or "")
    s = re.sub(r"[^A-Za-z\s\.]", " ", s)
    s = s.replace(".", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()

def lang_ok(tw: dict) -> bool:
    """Fast language gate using preprocessed fields."""
    lang = tw.get("lang")
    conf = float(tw.get("lang_conf", 0))
    if lang in ALLOWED_LANGS:
        return (lang != "en") or (conf >= LANG_MIN_CONF)
    return False

def in_time_window(tw: dict) -> bool:
    """Apply a fixed time window gate if provided."""
    if not TIME_WINDOW:
        return True
    try:
        t = int(tw.get("timestamp_ms", 0))
    except Exception:
        return True
    s, e = TIME_WINDOW
    return s <= t <= e

def pick_text_candidates(tweet: dict) -> List[Tuple[str, int]]:
    """
    Return candidate (text, weight) in order:
      1) qt_text (quoted original, most factual)
      2) rt_text (retweeted original)
      3) clean_text
      4) text_no_tags
    Each added at most once per tweet using a de-duplicate.
    """
    cands, seen = [], set()
    if tweet.get("is_quote") and tweet.get("qt_text"):
        t = tweet["qt_text"].strip()
        if t and t not in seen: cands.append((t, WEIGHT_QT)); seen.add(t)
    if tweet.get("is_retweet") and tweet.get("rt_text"):
        t = tweet["rt_text"].strip()
        if t and t not in seen: cands.append((t, WEIGHT_RT)); seen.add(t)
    t = (tweet.get("clean_text") or "").strip()
    if t and t not in seen: cands.append((t, WEIGHT_RAW)); seen.add(t)
    t = (tweet.get("text_no_tags") or "").strip()
    if t and t not in seen: cands.append((t, WEIGHT_RAW)); seen.add(t)
    return cands

TITLE_CHUNK_RE = re.compile(
    r'"([^"]{2,80})"|((?:[A-Z][a-z0-9\'&\-\:]+)(?:\s+(?:[A-Z][a-z0-9\'&\-\:]+)){0,5})'
)
def extract_titles_free(span: str) -> List[str]:
    found = set()
    for m in TITLE_CHUNK_RE.finditer(span or ""):
        s = (m.group(1) or m.group(2) or "").strip()
        if len(s.split()) >= 1:
            found.add(s)
    return list(found)


def select_extractor_for_award(award: str,
                                nominees_by_award: Dict[str, List[str]],
                                person_extractor=None):
    """
    Choose the appropriate extractor:
    work-type awards and person-type awards
    """
    if TITLE_AWARD_HINT.search(award):
        losers = { (x or "").lower() for x in nominees_by_award.get(award, []) }
        def extractor(span: str) -> List[str]:
            titles = extract_titles_free(span)
            return [t for t in titles if t.lower() not in losers]
        return extractor
    return person_extractor

# Award matching & local alignment
def best_award_match(span_text: str,
                      awards: List[str],
                      award_index: Dict[str, set],
                      min_jaccard: float,
                      min_anchor: int) -> Optional[str]:
    """
    Map to an official award name:
    extract "Best …" phrase if present else use entire span
    token Jaccard vs normalized awards
    require ≥ min_anchor anchor tokens to overlap.
    """
    phrase = BEST_PHRASE.search(span_text or "")
    probe = normalize_award(phrase.group(0)) if phrase else normalize_award(span_text or "")
    if not probe:
        return None
    probe_set = set(probe.split())
    best, best_score = None, 0
    for a in awards:
        anchors = award_index[a]
        if len(probe_set & anchors) < min_anchor:
            continue
        a_set = set(normalize_award(a).split())
        j = len(probe_set & a_set) / max(1, len(probe_set | a_set))
        if j > best_score:
            best, best_score = a, j
    return best if best_score >= min_jaccard else None

def award_winner_context(text: str,
                          awards: List[str],
                          award_index: Dict[str, set],
                          nominees_by_award: Dict[str, List[str]],
                          person_extractor,
                          min_jaccard: float,
                          min_anchor: int):
    """
    Given a tweet with a winning verb, then align (award, candidate) pairs by:
    "X wins Y"  : award on RIGHT, candidates on LEFT
    "Y goes to X": award on LEFT, candidates on RIGHT
    Fallback: try full text if local windows do not match an award.
    """
    m = WIN_VERB.search(text or "")
    if not m:
        return []
    left, right = text[:m.start()], text[m.end():]
    left_win  = " ".join(left.split()[-12:])
    right_win = " ".join(right.split()[:16])

    pairs = []

    # X wins Y
    aw = best_award_match(right_win, awards, award_index, min_jaccard, min_anchor)
    if aw:
        extractor = select_extractor_for_award(aw, nominees_by_award, person_extractor) or person_extractor
        left_cands = (extractor(left_win) or []) if extractor else []
        for c in left_cands:
            if c: pairs.append((aw, c))
    if not aw:
        aw = best_award_match(text, awards, award_index, min_jaccard, min_anchor)  # fallback

    # Y goes to X
    aw2 = best_award_match(left_win, awards, award_index, min_jaccard, min_anchor)
    if aw2:
        extractor = select_extractor_for_award(aw2, nominees_by_award, person_extractor) or person_extractor
        right_cands = (extractor(right_win) or []) if extractor else []
        for c in right_cands:
            if c: pairs.append((aw2, c))
    elif not aw2:
        _ = best_award_match(text, awards, award_index, min_jaccard, min_anchor)

    return pairs

#time gate 
def compute_time_threshold_ms(tweets: Iterable[dict],
                               trigger_res: List[re.Pattern],
                               pct: float) -> Optional[int]:
    """
    this is a lower time threshold (ms) so that only tweets at/after the
    `pct` quantile among trigger-containing tweets are kept.
    """
    ts = []
    for tw in tweets:
        txt = (tw.get("clean_text") or tw.get("text_no_tags") or tw.get("text") or "").strip()
        if any(p.search(txt) for p in trigger_res):
            try:
                ts.append(int(tw.get("timestamp_ms", 0)))
            except Exception:
                pass
    if not ts:
        return None
    ts.sort()
    k = max(0, min(len(ts) - 1, int(len(ts) * pct)))
    return ts[k]

# Merge & finalize
def safe_merge_actors_awards(votes: Dict[Tuple[str, str], int]) -> Dict[Tuple[str, str], int]:
    """
    Merge near-duplicates:
    keep award keys must match official naming upstream
    normalize person names (Title Case, punctuation removed)
    do not normalize work titles (preserve nominee spellings).
    """
    merged: Dict[Tuple[str, str], int] = defaultdict(int)
    for (award, person), cnt in votes.items():
        if not award or not person:
            continue
        merged[(award, canon_person(person))] += int(cnt)
    return dict(merged)

#Public API
def identify_winners(tweets: List[dict],
                     award_names: List[str],
                     nominees_by_award: Dict[str, List[str]],
                     *,
                     person_extractor=None,
                     strict_nominees: bool = False,
                     min_jaccard: float = MIN_JACCARD,
                     min_anchor: int = MIN_ANCHOR_OVERLAP,
                     time_pct: Optional[float] = None
                     ) -> tuple[Dict[tuple, int], Dict[str, str], Dict[str, List[tuple]]]:
    """
    Identify winners for the given awards.
    """
    # Pre-compile triggers
    trigger_res = [re.compile(p, re.IGNORECASE) for p in WIN_TRIGGERS]

    # time bound if needed
    dynamic_start = None
    if TIME_WINDOW is None and time_pct is not None:
        dynamic_start = compute_time_threshold_ms(tweets, trigger_res, time_pct)

    # Build index once and whitelist (as-is — award keys must already match)
    award_index = build_award_index(award_names)
    nom_map = {a: set(noms or []) for a, noms in (nominees_by_award or {}).items()}
    votes = defaultdict(int)

    for tw in tweets:
        # language and time gates 
        if not lang_ok(tw):
            continue
        if dynamic_start is not None:
            try:
                if int(tw.get("timestamp_ms", 0)) < dynamic_start:
                    continue
            except Exception:
                pass
        if not in_time_window(tw):
            continue

        # aggregate candidate texts (qt/rt/clean/no_tag) and de-duplicate per tweet
        per_tweet_seen = set()
        for text, weight in pick_text_candidates(tw):
            if not text or NON_FACTUAL_RE.search(text):
                continue
            # verb trigger gate
            if not any(p.search(text) for p in trigger_res):
                continue

            # local alignment around verb (award and candidate)
            pairs = award_winner_context(
                text, award_names, award_index, nominees_by_award,
                person_extractor, min_jaccard, min_anchor
            )

            # vote and whitelist filtering
            for award, candidate in pairs:
                if not award or not candidate:
                    continue
                if strict_nominees and award in nom_map and nom_map[award] and candidate not in nom_map[award]:
                    continue
                key = (award, candidate)
                if key in per_tweet_seen:
                    continue
                per_tweet_seen.add(key)
                votes[key] += weight

    # merge near-duplicates (award key preserved and person normalized)
    if votes:
        votes = safe_merge_actors_awards(votes)

    # produce winners and top-k lists per award
    grouped = defaultdict(list)
    for (award, candidate), c in votes.items():
        grouped[award].append((candidate, c))

    winners, topk = {}, {}
    for award, lst in grouped.items():
        lst_sorted = sorted(lst, key=lambda x: (-x[1], x[0]))
        topk[award] = lst_sorted
        winners[award] = lst_sorted[0][0]

    return dict(votes), winners, topk

