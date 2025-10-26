import re
from collections import defaultdict
from utils.helpers.text_matching import extract_person_names, merge_similar_entries
from utils.helpers.patterns import presenters_pattern
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

### HELPER FUNCTIONS & VARIABLES ###

PRES_RE = re.compile(presenters_pattern, re.I)

def normalize(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def strip_common_words(s):
    # Remove common words like "best", "in", "a", "for", "by", and dashes (with or without spaces)
    s = re.sub(r'\b(best|in|a|for|or|by)\b', '', s, flags=re.IGNORECASE)  # Remove common words
    s = re.sub(r'\s*-\s*', ' ', s)  # Remove dashes with or without spaces around them
    return s.strip()



### MAIN FUNCTIONS ###

def presenter_extraction_first_pass(data, awards, hosts):
    WORDS_TO_MATCH_AWARD_SHORT = 3
    WORDS_TO_MATCH_AWARD_LONG = 5

    norm_awards = {award: normalize(strip_common_words(award)) for award in awards}
    presenter_scores = {award: defaultdict(float) for award in awards}

    for tweet in data:
        text = tweet.get('clean_text') or tweet.get('text_no_tags') or tweet.get('text', '')
        norm_text = normalize(strip_common_words(text))

        # Determine the threshold based on the length of the stripped award name
        mentioned_awards = []
        for award, norm_award in norm_awards.items():
            award_words = len(norm_award.split())
            threshold = WORDS_TO_MATCH_AWARD_SHORT \
                                if award_words <= 6 \
                   else WORDS_TO_MATCH_AWARD_LONG
            
            if len(set(norm_award.split()) & set(norm_text.split())) >= threshold:
                mentioned_awards.append(award)

        if not mentioned_awards:
            continue

        # Check for presenter-related cues
        if PRES_RE.search(text):
            names = extract_person_names(text, context_text=text)  # Extract all names
            if not names:
                continue
            boost = 1.0 + (0.4 if tweet.get('is_retweet') else 0.0)

            # Exclude names that are in the list of hosts
            if hosts:
                names = [name for name in names if name not in hosts]

            for award in mentioned_awards:
                for name in set(names):
                    presenter_scores[award][name] += boost

    return {
        award: [n for n, _ in sorted(scores.items(), key=lambda x: -x[1])[:3]]
        for award, scores in presenter_scores.items()
    }

from difflib import SequenceMatcher

PRES_RE_BROAD = re.compile(
    r"\b(present|presenter|presented|presenting|introduce|announce|give|hand|award|"
    r"gave|giving|announced|introduced|revealed)\w*\b", re.I
)

# Perform a more general search for presenters for awards with no results after the first pass.
def presenter_extraction_second_pass(data, awards, hosts, first_pass_results):
    
    def is_award_match(norm_award, norm_text, relaxed_overlap=2, fuzzy_threshold=80):
        award_tokens = set(norm_award.split())
        text_tokens = set(norm_text.split())
        overlap_tokens = award_tokens & text_tokens

        # ignore meaningless overlaps like 'film', 'motion', 'picture' alone
        generic = {"film", "movie", "motion", "picture", "television", "tv", "series"}
        if overlap_tokens <= generic:
            return False

        # Require proportional coverage, not absolute count
        coverage = len(overlap_tokens) / max(1, len(award_tokens))
        if coverage >= 0.6 or len(overlap_tokens) >= relaxed_overlap:
            return True

        # fallback fuzzy match only for nearly exact wording
        similarity = SequenceMatcher(None, norm_award, norm_text).ratio()
        return similarity > (fuzzy_threshold / 100.0)



    norm_awards = {award: normalize(strip_common_words(award)) for award in awards}
    presenter_scores = {award: defaultdict(float) for award in awards}

    # Only rerun for awards that had few or no presenters
    incomplete_awards = [
        a for a, names in first_pass_results.items() if len(names) < 2
    ]

    for tweet in data:
        text = tweet.get('clean_text') or tweet.get('text_no_tags') or tweet.get('text', '')
        norm_text = normalize(strip_common_words(text))

        # --- identify awards mentioned in this tweet ---
        mentioned_awards = [
            award for award, norm_award in norm_awards.items()
            if award in incomplete_awards and is_award_match(norm_award, norm_text)
        ]
        
        if not mentioned_awards:
            continue


        # --- look for presenter cues ---
        if PRES_RE_BROAD.search(text):
            names = extract_person_names(text)
            if not names:
                continue

            boost = 0.8 + (0.2 if tweet.get('is_retweet') else 0.0)

            # apply softened host filtering
            for award in mentioned_awards:
                for name in set(names):
                    score_adj = 0.5 if hosts and name in hosts else 1.0
                    presenter_scores[award][name] += boost * score_adj

    # --- merge with first-pass results per award ---
    combined = {}
    for award in awards:
        combined_scores = defaultdict(float)

        # add second-pass scores
        if award in presenter_scores:
            for name, score in presenter_scores[award].items():
                combined_scores[name] += score

        # add first-pass names with fixed weight
        for name in first_pass_results.get(award, []):
            combined_scores[name] += 1.0

        # Merge similar names
        merged_scores = merge_similar_entries(combined_scores)

        # rank presenters per award
        ranked = sorted(merged_scores.items(), key=lambda x: -x[1])
        combined[award] = [n for n, _ in ranked[:3]]

    return combined
