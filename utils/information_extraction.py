# Imports
import re
import time
import json
import difflib
from collections import defaultdict, Counter
from utils.helpers.patterns import winning_patterns, host_patterns, award_patterns
from utils.helpers.text_matching import merge_similar_entries, merge_similar_actors_awards, \
    extract_person_names
from utils.helpers.award_merging import merge_normalized, calculate_tweet_weight, \
        merge_similar_awards_second_pass, extract_best_candidates
from utils.helpers.context_functions import award_winner_context, host_context
import spacy
nlp = spacy.load("en_core_web_sm")


AWARD_NAMES = [
    "best screenplay - motion picture",
    "best director - motion picture",
    "best performance by an actress in a television series - comedy or musical",
    "best foreign language film",
    "best performance by an actor in a supporting role in a motion picture",
    "best performance by an actress in a supporting role in a series, mini-series or motion picture made for television",  # Edge case 3
    "best motion picture - comedy or musical",
    "best performance by an actress in a motion picture - comedy or musical",
    "best mini-series or motion picture made for television",
    "best original score - motion picture",
    "best performance by an actress in a television series - drama",
    "best performance by an actress in a motion picture - drama",
    "cecil b. demille award",
    "best performance by an actor in a motion picture - comedy or musical",
    "best motion picture - drama",
    "best performance by an actor in a supporting role in a series, mini-series or motion picture made for television",
    "best performance by an actress in a supporting role in a motion picture",
    "best television series - drama",
    "best performance by an actor in a mini-series or motion picture made for television",
    "best performance by an actress in a mini-series or motion picture made for television",
    "best animated feature film",
    "best original song - motion picture",
    "best performance by an actor in a motion picture - drama",
    "best television series - comedy or musical",
    "best performance by an actor in a television series - drama",
    "best performance by an actor in a television series - comedy or musical"
]


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

    # Merge similar (second pass)
    # This second pass is to handle merging cases like:
    #   "best actor in a motion picture", "Best actor in a motion picture drama"
    #   "best song", "Best Original Song"
    #   "best actress", "best actress in a TV comedy or musical"
    # Distinguishing between "actor" and "actress"
    #   This way you don't accidentally merge "best actor XXX" and "best actress XXX"
    # Pick longer case when merging similar awards, as longer is generally better
    #   Or if one is contained within the other, pick the "parent"
    # Potentialyl use TFIDF (clustering) for later sophistication?
    # award_candidates = merge_similar_awards_second_pass(award_candidates)
    
    # Convert to list of tuples and sort by weight
    weighted_awards = [(award, weight) for award, weight in award_candidates.items()]
    best_candidates = extract_best_candidates(weighted_awards, score_factor=0.5)
    
    return [(k, v) for k, v in best_candidates.items()]
    # return best_candidates




# NOTE: Winners for Tian
def extract_winners_from_tweets(data, awards):
    return find_matches(data, winning_patterns, extract_function=extract_person_names,
                        context=awards, context_function=award_winner_context)

def extract_hosts_from_tweets(data, awards):
    return find_matches(data, host_patterns, extract_function=extract_person_names,
                        context=awards, context_function=host_context)


def process_tweets(data):
    print("Extracting awards...")
    awards = extract_awards_from_tweets(data)

    # print("Extracting winners...")
    # winners = extract_winners_from_tweets(data, awards)

    # print("Extracting hosts...")
    # hosts = extract_hosts_from_tweets(data, awards)

    # return winners, hosts, awards
    return awards
        

def pretty_print_results(awards):
    print("\n" + "="*50)
    print("AWARDS:")
    print("="*50)
    ground_truth_set = set(AWARD_NAMES)
    sorted_awards = sorted(awards.items(), key=lambda x: -x[1])
    for award, count in sorted_awards:
        if count > 10:
            max_similarity = max(
                difflib.SequenceMatcher(None, award.lower(), ground_truth_award.lower()).ratio()
                for ground_truth_award in ground_truth_set)
            print(f"{max_similarity:.2f}\t{award}: {count}")



if __name__ == "__main__":
    data_file = 'gg2013_preprocessed.jsonl'
    n = 10

    # Load the main data file
    gg_data = load_data(data_file)
    if gg_data:
        print(f"Loaded {len(gg_data)} items from {data_file}")

    # Measure time taken for process_tweets
    start_time = time.time()
    # winners, hosts, awards = process_tweets(gg_data)
    awards = process_tweets(gg_data)
    end_time = time.time()
    print(f"Process took {end_time-start_time:.2f} seconds")


    # Print top 40 weighted awards
    # print(f"\nTop 40/{len(awards)} Weighted Awards:")
    # print("=" * 60)
    # for i, (award, weight) in enumerate(awards[:40]):
    #     print(f"{i+1:2d}. {weight:6.2f} - '{award}'")    

    # Print all candidates with candidate_weight not equal to 0
    # Sort by descending candidate_weight, then alphabetically for tie-break

    print("\nCandidates with non-zero candidate_weight (sorted):")
    sorted_candidates = sorted(
        awards,
        key=lambda x: (-x[1], x[0])
    )
    for award_text, candidate_weight in sorted_candidates:
        print(f"{candidate_weight:.2f}\t{award_text}")

    # for award, score in sorted_candidates:
    #     max_similarity = max(
    #         difflib.SequenceMatcher(None, award.lower(), ground_truth_award.lower()).ratio()
    #         for ground_truth_award in set(AWARD_NAMES))
    #     print(f"{max_similarity:.2f}\t{award}: {score}")


