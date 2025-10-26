# Imports
import re
import time
import json
import difflib
from collections import defaultdict, Counter
from utils.helpers.patterns import award_patterns, presenters_pattern
from utils.helpers.text_matching import merge_similar_entries, merge_similar_actors_awards, extract_person_names
from utils.helpers.award_merging import merge_normalized, calculate_tweet_weight, extract_best_candidates
from utils.helpers.presenter_extraction import presenter_extraction_first_pass, presenter_extraction_second_pass
from utils.winners import identify_winners
# import spacy
# nlp = spacy.load("en_core_web_sm")


HOST_RE   = re.compile(r"\b(host|hosts|hosted|hosting)\b", re.I)
PAIR_HOST_RE = re.compile(
    r"\b(?:hosted\s+by|your\s+hosts|tonight'?s\s+hosts?|hosts?)\b", re.I
)
STRONG_HOST_RE = re.compile(
    r"\b("
    r"hosted\s+by|your\s+hosts?|tonight'?s\s+hosts?|are\s+hosting|as\s+hosts?|"
    r"co-?hosts?|co-?host(?:ing|ed)?|serving\s+as\s+hosts?"
    r")\b", re.I
)
FUTURE_RE = re.compile(r"\b(should|would|could|to\s+host|next\s+year|hope|wish|pls|please|let)\b", re.I)
SENT_SPLIT = re.compile(r"[.!?]+|\n+")
PRES_RE = re.compile(presenters_pattern, re.I)
QUOTED_TITLE_RE = re.compile(r"[“”\"']([^\"“”']{2,})[“”\"']")
TITLE_CASE_SEQ_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,})\b")
NOM_CUE_RE = re.compile(
    r"\b("
    r"nominee?s?|nominations?|noms?|contenders?|shortlist|line[-\s]?up|field|the\s+list|"
    r"include?s?|featuring|among|vs\.?|versus|competing|in\s+contention|"
    r"(?:is|are)\s+nominated\s+for|nominated\s+for|are\s+up\s+for|are\s+in\s+the\s+running\s+for|"
    r"best\s+[^:]{0,100}:"
    r")\b",
    re.I
)

LIST_SPLIT_RE = re.compile(r"\s*(?:,|/|;|\||•|·|\u2022|\u00b7|\s+and\s+|\s*&\s*|\s+vs\.?\s+|\s+versus\s+)\s*", re.I)

def _same_sentence_host_names(text: str):
    """
    1. Extract sentences
    2. Filter out sentences without strong host cues or presenter/future cues
    3. Extract names from remaining sentences
    4. Keep names that are within ~6 tokens of the host cue 
    """
    winners = []
    for sent in [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]:
        if not STRONG_HOST_RE.search(sent) or PRES_RE.search(sent) or FUTURE_RE.search(sent):
            continue

        names = extract_person_names(sent, context_text=sent)
        # require name within ~6 tokens of the host cue to avoid loose co-occurrence
        for n in names:
            near = re.search(
                rf"(?:\b{re.escape(n)}\b(?:\W+\w+){{0,6}}\W+(?:host|hosts|hosted|hosting))|"
                rf"(?:\b(?:host|hosts|hosted|hosting)\b(?:\W+\w+){{0,6}}\W+\b{re.escape(n)}\b)",
                sent, re.I
            )
            if near:
                winners.append(n)
    return winners


def expected_entity_kind(award_name: str) -> str:
    a = award_name.lower()
    title_hints  = [
        "screenplay", "original score", "score", "original song", "song",
        "motion picture", "picture", "film",
        "television series", "tv series", "series",
        "mini-series", "miniseries"
    ]
    person_hints = ["actor", "actress", "supporting", "performance", "director"]
    if any(h in a for h in title_hints):
        return "title"
    if any(h in a for h in person_hints):
        return "person"
    return "title"


def extract_title_like_candidates(text: str, nlp_doc=None):
    # Grab likely movie/series/song titles via quotes
    cands = set()

    for m in QUOTED_TITLE_RE.finditer(text):
        cands.add(m.group(1).strip())

    for m in TITLE_CASE_SEQ_RE.finditer(text):
        cands.add(m.group(1).strip())

    if nlp_doc:
        for ent in nlp_doc.ents:
            if ent.label_ in ("WORK_OF_ART", "ORG", "EVENT"):
                cands.add(ent.text.strip())

    # prune obvious phrases
    pruned = {t for t in cands if not re.search(r"\b(golden|globe|award|best|category|host|present)\b", t, re.I)}
    return list(pruned)


# Load tweets
def load_data(filepath):
    try:
        data = []
        with open(filepath, 'r', encoding='utf-8') as file:
            # Try JSONL format first (preprocessed data)
            if filepath.endswith('.jsonl'):
                for line in file:
                    if line.strip():
                        data.append(json.loads(line))
            else:
                # Original JSON format
                file.seek(0)
                data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return None


### DATA PROCESSING FUNCTIONS ###
def find_matches(data, patterns, extract_function, context=None, context_function=None):
    matches = defaultdict(int)
    for tweet in data:
        # choose cleanest text
        tweet_text = tweet.get('clean_text') or tweet.get('text_no_tags') or tweet.get('text', '')

        # check if tweet contains any keyword pattern
        has_pattern_context = any(re.search(pattern, tweet_text, re.IGNORECASE) for pattern in patterns)
        if not has_pattern_context:
            continue

        # apply context function if given
        extracted = context_function(tweet_text, context, extract_function) \
        if context else extract_function(tweet_text)
        for item in extracted:
            matches[item] += 1

    # merge
    if all(isinstance(k, tuple) for k in matches):
        return merge_similar_actors_awards(matches)
    return merge_similar_entries(matches)



def extract_awards_from_tweets(data):

    hashtags = Counter()
    for tweet in data:
        for hashtag in tweet['hashtags']:
            hashtags[hashtag] += 1
    most_common_hashtag = hashtags.most_common(1)[0][0]
    most_common_hashtag = re.split(r'(?<!\^)(?=[A-Z])', most_common_hashtag)[1:]
    print(f"Most common hashtag: {most_common_hashtag}")

    hashtags = Counter()
    for tweet in data:
        hashtags[tweet['rt_user']] += 1
        hashtags[tweet['qt_user']] += 1
    most_common_referenced = [tag for tag in hashtags.most_common(11) if tag[0] is not None][:10]  # Get top 10, drop None if present
    print(f"Most common referenced accounts: {[tag[0] for tag in most_common_referenced]}")

    # Awards that start with "Best"
    filtered_tweets = []
    for tweet in data:

        # run your existing regex extraction
        for pattern, side in award_patterns.items():
            
            # Match to regex pattern
            match = re.search(pattern, tweet['clean_text'])
            if not match:
                continue

            # get the left and right side of the match
            left, _, right = tweet['clean_text'].partition(match.group(0))
            award_text = left if side == 0 else right  # Identify which side the award will be on
            award_text = re.split(r'[.?!"]', award_text)[0]
            if ":" in award_text:  # Eliminate retweet text (e.g. get rid of "@CNNshowbiz:")
                award_text = award_text.split(":", 1)[-1]
        
            if " for " in award_text:
                cleaned = award_text.rsplit(" for ", 1)[0]
            cleaned = cleaned.rsplit(",", 1)[0].strip()  # Get everything before last comma
            cleaned = cleaned.split("and")[0]  # Get everything before "and", award names do not contain "and"
            cleaned = cleaned.split("#")[0]  # Remove trailing hashtags in tweets

            # Award names must be longer than 1 word
            if len(cleaned.split()) <= 1:  # Get rid of trimmed awards that are too short
                continue

            # START Get rid of awards that contain the most common hashtag (should be Golden Globes for this dataset)
            #   This way remove cases like "... winner in the Golden Globes!"
            hashtag_in_string = True
            for word in most_common_hashtag:
                if word.lower() not in cleaned.lower():
                    hashtag_in_string = False
            if hashtag_in_string:
                continue
            # END
            
            # Skip awards that contain numbers, no award name contains numbers.
            if any(char.isdigit() for char in award_text):
                continue
                
            # If 'cleaned' ends in " at" or " goes to", remove that and everything after
            #   These two phrases indicate a phrase afterwards that is not related to an award name.
            if cleaned.strip().endswith(" at"):
                cleaned = cleaned.rsplit(" at", 1)[0]
            elif cleaned.strip().endswith(" goes to"):
                cleaned = cleaned.rsplit(" goes to", 1)[0]
            

            # If 'best' is present, but not at the start, remove everything before 'best'
            # This case also removes all awards that don't start with best.
            cleaned_lower = cleaned.lower()
            best_idx = cleaned_lower.find("best")
            if best_idx == -1:
                continue
            else:
                if best_idx != 0:
                    # Remove everything before 'best'
                    cleaned = cleaned[best_idx:].strip()
            

            # If " is " is in cleaned, and pattern is r'\b\swinner of\s\b', then remove " is " and everything after
            if " is " in cleaned and pattern == r'\b\swinner of\s\b':
                cleaned = cleaned.split(" is ", 1)[0].strip()

            # Replace dashes and slashes with NO SPACES AROUND THEM with a space
            cleaned = re.sub(r'(?<=\w)-(?=\w)', ' ', cleaned)
            cleaned = re.sub(r'(?<=\w)/(?=\w)', ' ', cleaned)

            # Remove parentheses and replace '(' with '- ' if a subsection of the string is surrounded by them
            def paren_to_dash(s):
                # This replaces (TEXT) with - TEXT
                # It will turn "... (foo) ..." into "... - foo ..."
                return re.sub(r'\(([^)]+)\)', r'- \1', s)
            cleaned = paren_to_dash(cleaned)


            # Eliminate unnecessary phrases after "for":
            #   "Don Cheadle *wins* Best Actor - Motion Picture FOR his amazing performances this year."
            for_match = re.search(r'\bfor\b\s+(\w+)', cleaned, re.IGNORECASE)
            if for_match:
                word_after_for = for_match.group(1).lower()
                if word_after_for != "television":
                    # remove "for" and everything after
                    cleaned = cleaned[:for_match.start()].strip()
            
            # Clean cases like:
            #   "Ben Affleck *won* Best Director - Motion Picture, YET people still won't consider him for the Emmys!""
            if " yet " in cleaned:
                cleaned = cleaned.split(" yet ", 1)[0].strip()
            
            # Common issues with matches that result in not matching
            #    (is this allowed?)
            cleaned = cleaned.lower()
            cleaned = cleaned.replace("tv", "television")
            cleaned = cleaned.replace("best actor", "best performance by an actor")
            cleaned = cleaned.replace("best actress", "best performance by an actress")


            # Add to list of tweets
            filtered_tweets.append((tweet, cleaned.strip(), pattern))


    print(f"Found {len(filtered_tweets)} results")

    
    # Weighting filtered tweets:
    #   Higher if:
    #       - Starts with best
    #       - more than 50% of words are title case
    #       - 4 or more words
    #       - Referenced by most common referenced accounts
    #   Lower if:
    #       - starts with lowercase "the", "[Ss]o", "[Bb]ut", "[Aa]\s", "[Aa]nd"
    #       - contains # or @ or "i think" or "\simo\s", "\sbig\s" 


    # Aggregate award candidates with weighted scoring
    award_candidates = defaultdict(float)
    
    for tweet, cleaned_award, pattern in filtered_tweets:
        weight = calculate_tweet_weight(tweet, cleaned_award, most_common_referenced)
        award_candidates[cleaned_award] += weight


    # Merge similar awards (first pass)
    award_candidates = merge_normalized(award_candidates)
    
    # Convert to list of tuples and sort by weight
    weighted_awards = [(award, weight) for award, weight in award_candidates.items()]
    # Best candidates weights the list of awards by common features found in awards
    #   and selects accordingly
    best_candidates = extract_best_candidates(weighted_awards, score_factor=0.5)
    list_of_awards = [k for k, v in best_candidates.items()]


    # r'\b(([A-Z][a-z]*|[A-Z].)\s)+[Aa]ward\b'


    second_award_group = defaultdict(int)
    for tweet in data:
        match = re.search(
            r'\b(([A-Z][a-z]*|[A-Z].)\s){3,4}[Aa]ward\b', 
            tweet['clean_text']
        )
        
        if not match:
            continue

        match_string = match.group(0)

        win_condition_words = ["win", "achievement", "present", "receive"]
        invalid_award_words = ["the", "is", "just", " for ", "globe"]
        match_string_lower = match_string.lower()
        # Skip if any win condition or invalid award word is in the match
        if any(word in match_string_lower for word in win_condition_words + invalid_award_words):
            continue

        second_award_group[match_string_lower] += 1
    
    second_group_merged = merge_normalized(second_award_group)
    if second_group_merged:
        # Find key with highest value
        best_award = max(second_group_merged.items(), key=lambda item: item[1])[0]
        list_of_awards.append(best_award)

    return list_of_awards




def extract_winners_from_tweets(data, awards, nominees_by_award=None):
    if nominees_by_award is None:
        nominees_by_award = {}
    
    # Use the identify_winners function from winners.py
    _, winners, topk = identify_winners(
        tweets=data,
        award_names=awards,
        nominees_by_award=nominees_by_award,
        person_extractor=extract_person_names,
        strict_nominees=False  # Allow non-nominees to be winners
    )
    
    return winners, topk

def extract_hosts_from_tweets(data, awards):
    """
    Basic idea: Sentence level filtering
`   1. Host announcements happen early (so look at timestamp), so we look for relatively early tweets
    2. Iterate through tweets
    3. Skip award related tweets
    4. Get person names with strong host-cue
    5. Accumulate evidence and add to scores
    6. Accumulate evidence of co hosting (both likely will be hosts)
    7. Return top hosts
    
    """
    # Running "tally" of how much evidence each candidate has
    scores = defaultdict(float)
    start_ts = min(
        (t.get("timestamp_ms") for t in data
         if isinstance(t.get("timestamp_ms"), int)
         and STRONG_HOST_RE.search(
             (t.get('clean_text') or t.get('text_no_tags') or t.get('text',''))
         )),
        default=None
    )

    for tw in data:
        text = tw.get('clean_text') or tw.get('text_no_tags') or tw.get('text', '')
        if any(re.search(re.escape(a), text, re.I) for a in awards):
            continue

        names = _same_sentence_host_names(text)
        if not names:
            continue
        boost = 1.0 + (0.4 if tw.get('is_retweet') else 0.0)
        ts = tw.get('timestamp_ms')
        if start_ts and isinstance(ts, int):
            mins = max(0, (ts - start_ts) / 60000.0)
            if mins <= 60: boost += 0.6
            elif mins <= 120: boost += 0.2

        for n in set(names):
            scores[n] += boost
    pair_counts = defaultdict(float)
    for tw in data:
        text = tw.get('clean_text') or tw.get('text_no_tags') or tw.get('text', '')
        if any(re.search(re.escape(a), text, re.I) for a in awards):
            continue
        # sentences that already passed strong-cue filters
        sents = [s for s in SENT_SPLIT.split(text) if s and STRONG_HOST_RE.search(s) and not (PRES_RE.search(s) or FUTURE_RE.search(s))]
        for s in sents:
            ns = list(set(extract_person_names(s, context_text=s)))
            if len(ns) >= 2:
                # count only if names appear around the host cue with "and"/comma (co-host phrasing)
                if re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b.*\b(and|,)\b.*\b[A-Z][a-z]+\s+[A-Z][a-z]+\b.*\b(host|hosts|hosted|hosting)\b", s, re.I):
                    for i in range(len(ns)):
                        for j in range(i+1, len(ns)):
                            a, b = sorted((ns[i], ns[j]))
                            pair_counts[(a,b)] += 1.0

    # choose pair if both individually strong and co-mentioned
    if pair_counts:
        (a,b), _ = max(pair_counts.items(), key=lambda kv: kv[1])
        if scores.get(a,0) >= 5 and scores.get(b,0) >= 5:
            return {a: scores[a], b: scores[b]}

    top = sorted(scores.items(), key=lambda x: -x[1])
    return dict(top[:2])


def extract_presenters_from_tweets(data, awards, hosts=None):
    # First pass: Use the more specific presenter extraction logic
    first_pass = presenter_extraction_first_pass(data, awards, hosts)

    # Second pass: Use the more general presenter extraction logic
    second_pass = presenter_extraction_second_pass(data, awards, hosts, first_pass)

    # Combine results from both passes
    combined_results = {**first_pass, **second_pass}
    return combined_results

def _same_sentence_nominees_for_award(text: str, award_name: str):
    """
    Higher recall, still cheap:
      - sentence must mention THIS award
      - prefer sentences with nominee cues OR a colon after "Best X"
      - skip clear winner/presenter/host lines
      - expand comma/'and' lists; extract people/titles per award type
    """
    if not re.search(re.escape(award_name), text, re.I):
        return []

    kind = expected_entity_kind(award_name)
    out = []

    for sent in (s.strip() for s in SENT_SPLIT.split(text) if s.strip()):
        # light skips to avoid single-winner
        if re.search(r"\b(won|wins|winner|awarded\s+to|goes\s+to)\b", sent, re.I):
            continue
        if re.search(r"\b(present|presenter|presenting|introduc|announce)\w*\b", sent, re.I):
            continue
        if re.search(r"\b(host|hosts|hosted|hosting)\b", sent, re.I):
            continue

        listy_hits = len(LIST_SPLIT_RE.split(sent)) - 1
        if not (NOM_CUE_RE.search(sent) or ":" in sent or listy_hits >= 2):
            continue

        # If colon/dash present, focus on RHS; else whole sentence
        parts = re.split(r":|-+\s*", sent, maxsplit=1)
        segment = parts[1].strip() if len(parts) == 2 and parts[1].strip() else sent

        if kind == "person":
            for chunk in LIST_SPLIT_RE.split(segment):
                chunk = chunk.strip()
                if not chunk:
                    continue
                out.extend(extract_person_names(chunk, context_text=segment))
        else:
            items = set()
            for chunk in LIST_SPLIT_RE.split(segment):
                chunk = chunk.strip()
                if not chunk:
                    continue
                items.update(extract_title_like_candidates(chunk))
            if not items:
                items.update(extract_title_like_candidates(segment))
            out.extend(items)

    return out

def extract_nominees_from_tweets(data, awards):
    # counts per award
    counts = {a: defaultdict(int) for a in awards}

    for tw in data:
        text = tw.get('clean_text') or tw.get('text_no_tags') or tw.get('text', '')
        if not text:
            continue
        for award in awards:
            cands = _same_sentence_nominees_for_award(text, award)
            for c in set(cands):
                counts[award][c] += 1

    nominees = {}
    for award, tally in counts.items():
        if not tally:
            nominees[award] = []
            continue
        merged = merge_similar_entries(tally)
        if merged:
            top_score = max(merged.values())
            cutoff = max(1, int(0.10 * top_score))
            ordered = sorted(merged.items(), key=lambda x: (-x[1], x[0]))
            filtered = [n for n, c in ordered if c >= cutoff]
            nominees[award] = filtered[:12]
        else:
            nominees[award] = []
    return nominees

def process_tweets(data, ground_truth_awards, ground_truth_nominees=None):
    print("Extracting awards...")
    awards = extract_awards_from_tweets(data)
    # awards = []

    print("Extracting winners...")
    winners, winner_candidates = extract_winners_from_tweets(data, ground_truth_awards, ground_truth_nominees)
    # winners, winner_candidates = ([], {"":([])})

    print("Extracting hosts...")
    hosts =  extract_hosts_from_tweets(data, ground_truth_awards)

    print("Extracting presenters...")
    presenters = extract_presenters_from_tweets(data, ground_truth_awards, hosts)

    print("Extracting nominees...")
    nominees = extract_nominees_from_tweets(data, ground_truth_awards)

    return (winners, winner_candidates), hosts, awards, presenters, nominees
