# imports
import re
import spacy
from difflib import SequenceMatcher
from collections import defaultdict

# load spaCy language model
nlp = spacy.load("en_core_web_sm")


# get the names of people
#   use regex and spaCy to identify names
def extract_person_names(text):

    def is_valid_person_name(name):
        pattern = r"^[A-Z][a-z]*(?:\s[A-Z][a-z]*)*$"
        return bool(re.match(pattern, name))

    doc = nlp(text)
    person_names = []
    
    for ent in doc.ents:
        if ent.label_ == "PERSON" and is_valid_person_name(ent.text):
            person_names.append(ent.text)
    
    return person_names


''' get the names of awards
multiple step process !!!
 1. define is_valid_award_name function
    - this function checks if a name is a valid award name
      by looking for keywords and using regex to check for
      title case or all caps patterns
 2. use spaCy labels (WORK_OF_ART, ORG, EVENT) to extract awards
    - these were the closest matching based on what I found
      https://stackoverflow.com/questions/70835924/how-to-get-a-description-for-each-spacy-ner-entity#answer-75317040
 3. use regex patterns to extract awards
    - these patterns are based on common award naming types
      trying to match them as closely as possible
 4. contextual award mentions using regex
    - same as 3 but using different patterns for different
      sentence matching

the three steps of extractions all add to the same list (not duplicates)
   so three methdods of finding award names.
   the final list is merged and returned
'''
def extract_awards(text):
    
    # step 1: define is_valid_award_name()
    def is_valid_award_name(name):
        name = name.strip()
        
        # needs to have  award-related keywords
        award_keywords = ['best', 'outstanding', 'award', 'category']
        if not any(keyword in name.lower() for keyword in award_keywords):
            return False
        
        # check for title case (Best Actor) or all caps pattern with>= 2 words
        title_case_pattern = r'^[A-Z][a-z]*(?:\s+[A-Z][a-z]*)+$'  # At least 2 title case words
        all_caps_pattern = r'^[A-Z]+(?:\s+[A-Z]+)+$'              # At least 2 all caps words
        if not (re.match(title_case_pattern, name) or re.match(all_caps_pattern, name)):
            return False
            
        return True
    
    doc = nlp(text)
    awards = []
    
    # step 2: use spaCy to extract from named entities (WORK_OF_ART, ORG, EVENT)
    for ent in doc.ents:
        if ent.label_ in ["WORK_OF_ART", "ORG", "EVENT"] and is_valid_award_name(ent.text):
            awards.append(ent.text)
    
    # step 3: use patterns for extracting common award naming types
    award_patterns = [
        r'\bBest\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',         # ex: Best Actor, Best Motion Picture
        r'\bOutstanding\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # ex: Outstanding Performance
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Award',        # ex: Supporting Actor Award
    ]
    
    for pattern in award_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if is_valid_award_name(match):
                if match not in awards:  # make sure to not get duplicates
                    awards.append(match)
    
    # step 4: contextual award mentions using regex
    context_patterns = [
        r'nominated\s+for\s+([A-Z][^.!?]*)',       # ex: "nominated for Best Actor"
        r'category\s+(?:is\s+)?([A-Z][^.!?]*)',    # ex: "category is Best Picture"
        r'goes\s+to\s+\w+\s+for\s+([A-Z][^.!?]*)'  # ex: "goes to John for Best Actor"
    ]

    for pattern in context_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Clean up the match and validate
            clean_match = re.sub(r'[.!?].*$', '', match).strip()
            if is_valid_award_name(clean_match):
                if clean_match not in awards:  # make sure to not get duplicates
                    awards.append(clean_match)
    
    return awards


# merge similar names including partial matches and misspellings
def merge_similar_entries(counts):

    def similarity_ratio(a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def get_name_for_comparison(key):
        if isinstance(key, tuple):
            return key[1]  # for (award, winner) tuples, compare winner name
        return key

    def get_award_for_comparison(key):
        if isinstance(key, tuple):
            return key[0]  # for (award, winner) tuples, compare award name
        return key

    merged_counts = defaultdict(int)
    processed = set()
    
    # sort  by count (descending), prioritize more frequent names
    sorted_names = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    for name, count in sorted_names:
        if name in processed:
            continue
            
        # canonical name is most frequent version of name
        canonical_name = name
        canonical_award = get_award_for_comparison(canonical_name)
        total_count = count
        processed.add(name)
        
        # get the name part for comparison
        name_for_comparison = get_name_for_comparison(name)
        canonical_name_for_comparison = get_name_for_comparison(canonical_name)
        
        # look for similar names to merge
        for other_name, other_count in sorted_names:
            if other_name in processed:
                continue
            
            # for tuples, also check if they have the same award
            other_award_for_comparison = get_award_for_comparison(other_name)
            if isinstance(name, tuple) and canonical_award != other_award_for_comparison:
                continue
            
            other_name_for_comparison = get_name_for_comparison(other_name)
            should_merge = False
            
            # case 1: one name is contained in another ("Amy" in "Amy Poehler")
            if (name_for_comparison.lower() in other_name_for_comparison.lower().split() or 
                    other_name_for_comparison.lower() in name_for_comparison.lower().split()):
                should_merge = True
                # use longer name as canonical
                if len(other_name_for_comparison) > len(canonical_name_for_comparison):
                    canonical_name = other_name
                    canonical_name_for_comparison = other_name_for_comparison
            
            # case 2: high similarity (misspellings, typos)
            elif similarity_ratio(name_for_comparison, other_name_for_comparison) > 0.85 and \
                    similarity_ratio(canonical_award, other_award_for_comparison) > 0.7:
                should_merge = True
                # keep more common name as canonical
                if other_count > count:
                    canonical_name = other_name
                    canonical_name_for_comparison = other_name_for_comparison
                    canonical_award = other_award_for_comparison
            
            if should_merge:
                total_count += other_count
                processed.add(other_name)
        
        merged_counts[canonical_name] = total_count
    
    return dict(merged_counts)