# imports
import re
import spacy
from difflib import SequenceMatcher
from collections import defaultdict

# load spaCy language model
nlp = spacy.load("en_core_web_sm")

def is_valid_person_name(name, context=""):
    if not name:
        return False
    name = name.strip()

    # filter out awards/hosting context
    if re.search(r"\b(golden|globes?|awards?|academy|oscars?|emmys?|grammys?|hosting?|hosted|category|best)\b",
                 name, re.IGNORECASE):
        return False

    # tokenize “words” and require at least 2 tokens unless mononym
    # this way we know it's a name
    parts = [p for p in name.split() if re.match(r"^[A-Za-z][A-Za-z\-'’]*$", p)]

    # capitalization
    for p in parts:
        if not re.match(r"^[A-Z][a-z]+(?:[-'][A-Z][a-z]+)*$", p):
            return False
    
    if re.search(r"\d|[@#]", name):
        return False

    return True

# get the names of people
#   use regex and spaCy to identify names
def extract_person_names(text, *, context_text=None):
    doc = nlp(text)
    names = []
    
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue
        candidate = ent.text.strip()
        if is_valid_person_name(candidate, context=context_text or text):
            names.append(candidate)
    
    return names


''' get the names of awards
'''
def extract_awards(tweets:list):
    # If right side of dash looks like person
    #    remove it
    def truncate_after_award(candidate: str):
        if "-" not in candidate:
            return candidate.strip()

        left, right = candidate.split("-", 1)
        doc_right = nlp(right.strip())

        # Heuristic: if the right side starts with a PERSON/ORG/PROPN/DET+NOUN combo → winner section
        first_token = doc_right[0]
        if (first_token.ent_type_ in {"PERSON", "ORG"} or
            first_token.pos_ in {"PROPN"} or
            any(ent.label_ in {"PERSON", "ORG"} for ent in doc_right.ents)):
            return left.strip()        # discard winner part
        return candidate.strip()
    

    award_fingerprints = {
        "dash_idx": [2,3,8,9],
        "comma_idx": [10,11],
        "dot_idx": [1]
    }
    
    award_candidates = defaultdict(int)
    
    for tweet in tweets:
        candidate = truncate_after_award(tweet.strip()).lower()
        
        split_candidate = candidate.split()

        if len(split_candidate) - split_candidate.count('-') < 4 \
                or len(split_candidate) - split_candidate.count('-') > 15\
                or 'and' in split_candidate:
            continue
                        
        if '-' in split_candidate:
            if split_candidate.count('-') > 2:
                continue

            if len( candidate.split('-')[-1].split() ) > 3:
                continue
            
            dash_idx = split_candidate.index('-')
            if dash_idx in award_fingerprints['dash_idx']:
                award_candidates[candidate] += 1
                continue
        
        if ',' in split_candidate:
            if split_candidate.count(',') != 1:
                continue

            comma_idx = split_candidate.index(',')
            if comma_idx in award_fingerprints['comma_idx']:
                award_candidates[candidate] += 1
                continue
        
        if '.' in split_candidate:
            if split_candidate.count('.') != 1:
                continue
            
            dot_idx = split_candidate.index('.')
            if dot_idx in award_fingerprints['dot_idx']:
                award_candidates[candidate] += 1
                continue
    
    return award_candidates




# Decide if two names should be merged based on substring or similarity
def _should_merge(a: str, b: str, similarity_thresh: float = 0.85):
    if a.lower() in b.lower().split() or b.lower() in a.lower().split():
        return True, 1  # substring match
    if SequenceMatcher(None, a.lower(), b.lower()).ratio() > similarity_thresh:
        return True, 2  # high similarity
    return False, 0


# merge similar names including partial matches and misspellings
def merge_similar_entries(counts):

    merged_counts = defaultdict(int)
    processed = set()
    
    # sort  by count (descending), prioritize more frequent names
    sorted_names = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    for name, count in sorted_names:
        if name in processed:
            continue
            
        # canonical name is most frequent version of name
        canonical_name = name
        total_count = count
        processed.add(name)
        
        # look for similar names to merge
        for other_name, other_count in sorted_names:
            if other_name in processed:
                continue
                
            should_merge, case = _should_merge(name, other_name)
            
            if should_merge:
                if case == 1 and len(other_name) > len(canonical_name):
                        canonical_name = other_name
                elif case == 2 and other_count > count:
                        canonical_name = other_name
                total_count += other_count
                processed.add(other_name)
        
        merged_counts[canonical_name] = total_count
    
    return dict(merged_counts)
