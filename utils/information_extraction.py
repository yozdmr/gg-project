# Imports
import re
import time
import json
from collections import defaultdict
from utils.helpers.patterns import winning_patterns, host_patterns, award_patterns
from utils.helpers.text_matching import merge_similar_entries, merge_similar_actors_awards, \
    extract_person_names, extract_awards
from utils.helpers.context_functions import award_winner_context
# import gender_guesser as gender

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
PRES_RE   = re.compile(r"\b(present|presenter|presenting|introduc|announce)\w*\b", re.I)
FUTURE_RE = re.compile(r"\b(should|would|could|to\s+host|next\s+year|hope|wish|pls|please|let)\b", re.I)
SENT_SPLIT = re.compile(r"[.!?]+|\n+")

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

        # if tweet.get('is_quote', False):
        #     tweet_text += " " + tweet.get('qt_text', '')
        
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
    return find_matches(data, award_patterns, extract_awards)

# NOTE: Winners for Tian
def extract_winners_from_tweets(data, awards):
    return find_matches(data, winning_patterns, extract_function=extract_person_names,
                        context=awards, context_function=award_winner_context)

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

def process_tweets(data):
    print("Extracting awards...")
    awards = extract_awards_from_tweets(data)

    print("Extracting winners...")
    winners = extract_winners_from_tweets(data, awards)

    print("Extracting hosts...")
    hosts = extract_hosts_from_tweets(data, awards)

    return winners, hosts, awards
        

def pretty_print_results(winners, hosts, awards, min_count=10):
    print("\n" + "="*50)
    print("WINNERS:")
    print("="*50)
    grouped_winners = defaultdict(list)
    for (award, winner), count in winners.items():
        if count >= min_count:
            grouped_winners[award].append((winner, count))
    for award, winner_list in grouped_winners.items():
        print(award)
        for winner, count in sorted(winner_list, key=lambda x: -x[1]):
            print(f"\t{winner}: {count}")

    print("\n" + "="*50)
    print("HOSTS:")
    print("="*50)
    for host, count in hosts.items():
        if count >= min_count:
            print(f"{host}: {count}")

    print("\n" + "="*50)
    print("AWARDS:")
    print("="*50)
    for award, count in awards.items():
        if count >= min_count:
            print(f"{award}: {count}")



if __name__ == "__main__":
    data_file = 'gg2013_preprocessed.jsonl'
    n = 10

    # Load the main data file
    gg_data = load_data(data_file)
    if gg_data:
        print(f"Loaded {len(gg_data)} items from {data_file}")

    # Measure time taken for process_tweets
    start_time = time.time()
    winners, hosts, awards = process_tweets(gg_data)
    end_time = time.time()
    print(f"Process took {end_time-start_time:.2f} seconds")


    new_winners = {}
    for (award, winner), count in winners.items():
        if award not in new_winners:
            new_winners[award] = []
        new_winners[award].append((winner, count))

    # Print matches
    pretty_print_results(winners, hosts, awards, min_count=n)
    
