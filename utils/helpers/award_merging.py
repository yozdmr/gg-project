import re
from difflib import SequenceMatcher


def calculate_tweet_weight(tweet, award_text, most_common_referenced): 
    weight = 1.0
    
    # Positive weights
    if award_text.lower().startswith('best'):
        weight += 0.8
    
    # If contains exactly one dash, add +0.3 weight
    if award_text.count('-') == 1:
        weight += 0.3
    
    # Check if more than 50% of words are title case
    words = award_text.split()
    if words:
        title_case_words = sum(1 for word in words if word.istitle())
        if title_case_words / len(words) > 0.5:
            weight += 0.3
    
    # 4 or more words
    if len(words) >= 4:
        weight += 0.2
    
    # Referenced by most common referenced accounts
    rt_user = tweet.get('rt_user')
    qt_user = tweet.get('qt_user')
    referenced_accounts = [account[0] for account in most_common_referenced]
    if rt_user in referenced_accounts or qt_user in referenced_accounts:
        weight += 0.3
    
    # Negative weights
    # Check for problematic starts
    problematic_starts = ['the', 'so', 'but', 'a', 'and', 'an', 'than']
    first_word = words[0].lower() if words else ""
    if first_word in problematic_starts:
        weight -= 0.4
    
    # Check for problematic content
    tweet_text = tweet.get('clean_text', '').lower()
    problematic_content_patterns = ['#', '@', ' big ']
    opinionated_patterns = ['i think', ' imo ', ' people\'s choice ', 'definitely', ' great ']

    # Penalize for problematic (spammy or noisy) content
    for pattern in problematic_content_patterns:
        if pattern in tweet_text:
            weight -= 0.4
            break  # Only subtract once per tweet

    # Penalize for opinionated language
    for pattern in opinionated_patterns:
        if pattern in tweet_text:
            weight -= 1
            break  # Only subtract once per tweet
    
    return weight



def normalize_award_name(name):
    # Remove extra spaces, convert to lowercase
    normalized = re.sub(r'\s+', ' ', name.lower().strip())
    # Remove common stop words - but keep important words like "original"
    stop_words = {'the', 'a', 'an', 'and', 'or', 'in', 'of', 'for', 'by', 'award', 'best'}
    words = [w for w in normalized.split() if w not in stop_words]
    return ' '.join(words)



def merge_normalized(awards, threshold=85):
    normalized_map = {}
    for award, weight in awards.items():
        normalized = normalize_award_name(award)
        best_match = None
        best_score = 0
        
        for existing_normalized in normalized_map:
            score = SequenceMatcher(None, normalized, existing_normalized).ratio() * 100
            if score >= threshold and score > best_score:
                best_match = existing_normalized
                best_score = score
        
        if best_match:
            original_name = normalized_map[best_match]['original']
            if weight > normalized_map[best_match]['weight']:
                normalized_map[best_match] = {'original': award, 'weight': weight}
            else:
                normalized_map[best_match]['weight'] += weight
        else:
            normalized_map[normalized] = {'original': award, 'weight': weight}
    
    return {data['original']: data['weight'] for data in normalized_map.values()}


def extract_best_candidates(awards, score_factor=0.6):
    best_candidates = {}
    for award, weight in awards:
        in_a_count = award.lower().count(" in a ")
        dash_count = award.lower().count(" - ")
        made_for_count = award.lower().count(" made for ")

        candidate_weight = 0.0
        if dash_count == 1:
            candidate_weight += 1
        
        if in_a_count >= 1:
            candidate_weight += 0.9
        if in_a_count == 2:
            candidate_weight += 0.3
        
        if made_for_count == 1:
            candidate_weight += 0.8
        
        if candidate_weight != 0.0:
            best_candidates[(award, weight)] = candidate_weight
    
    # Normalize weights to the range 0-1
    weights = [elem[1] for elem in best_candidates.keys()]
    wmin, wmax = min(weights), max(weights)
    normalized_weights = [(w - wmin) / (wmax - wmin) if wmax > wmin else 0.0 for w in weights]

    # Add normalized weight to candidate_weight
    # First, create a mapping of (award, weight) -> normalized_weight
    normalized_weight_map = {
        key: norm_w for key, norm_w in zip(best_candidates.keys(), normalized_weights)
    }
    # Now, update each value in best_candidates by adding the normalized weight
    best_candidates = {
        k[0]: v + normalized_weight_map[k]*score_factor for k, v in best_candidates.items()
    }

    return best_candidates

def extract_gender_keywords(award_name):
    gender_keywords = {
        'actor': ['actor', 'male'],
        'actress': ['actress', 'female']
    }
    
    normalized = award_name.lower()
    found_genders = set()
    for gender, keywords in gender_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            found_genders.add(gender)
    
    return found_genders

def find_award_subsets(awards):
    award_names = list(awards.keys())
    subset_map = {}
    
    for award in award_names:
        subset_map[award] = []
        norm_award = normalize_award_name(award)
        set_award = set(norm_award.split())
        
        for other_award in award_names:
            if award == other_award:
                continue
                
            norm_other = normalize_award_name(other_award)
            set_other = set(norm_other.split())
            
            # Check if current award is a subset of the other award
            if set_award.issubset(set_other) and len(set_award) < len(set_other):
                subset_map[award].append(other_award)
            # Handle exact matches - prefer title case version
            elif norm_award == norm_other and norm_award != "":
                # If they normalize to the same thing, prefer the one with more title case
                title_case_award = sum(1 for word in award.split() if word.istitle())
                title_case_other = sum(1 for word in other_award.split() if word.istitle())
                
                if title_case_award < title_case_other:
                    subset_map[award].append(other_award)
    
    return subset_map

def choose_better_award_name(award1, award2, score1, score2):
    # If one is significantly longer, check if it has sufficient score
    if len(award1) > len(award2):
        if score1 >= score2 * 0.25:  # Longer award has at least 25% of shorter award's score
            return award1
        else:
            return award2
    elif len(award2) > len(award1):
        if score2 >= score1 * 0.25:  # Longer award has at least 25% of shorter award's score
            return award2
        else:
            return award1
    
    # If same length, prefer the one with more title case words
    title_case1 = sum(1 for word in award1.split() if word.istitle())
    title_case2 = sum(1 for word in award2.split() if word.istitle())
    
    if title_case1 > title_case2:
        return award1
    else:
        return award2


# Important
def merge_similar_awards_second_pass(awards):
    if not awards:
        return awards
    
    # Find subset relationships
    subset_map = find_award_subsets(awards)
    
    # Create a copy of awards to work with
    result_awards = awards.copy()
    
    # Process each award that has subsets, but only if it still exists
    for award, parent_awards in subset_map.items():
        if not parent_awards or award not in result_awards:
            continue
        
        # For each parent award, decide whether to merge or distribute
        award_score = result_awards[award]
        
        for parent_award in parent_awards:
            if parent_award not in result_awards:
                continue
                
            parent_score = result_awards[parent_award]
            
            # Choose the better award name based on length and score
            better_name = choose_better_award_name(award, parent_award, award_score, parent_score)
            
            if better_name == parent_award:
                # Keep parent, add award's score to it
                result_awards[parent_award] += award_score
            else:
                # Replace parent with award, add parent's score to award
                result_awards[award] = award_score + parent_score
                del result_awards[parent_award]
                break  # Only process one parent per award
        
        # Remove the subset award if it wasn't chosen as the better name
        if award in result_awards:
            del result_awards[award]
    
    return result_awards
