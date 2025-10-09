# Imports
import re
import time
import json
from collections import defaultdict
from utils.helpers.patterns import winning_patterns, host_patterns, award_patterns
from utils.helpers.text_matching import merge_similar_entries, merge_similar_actors_awards, \
    extract_person_names, extract_awards
from utils.helpers.context_functions import award_winner_context, host_context
# import gender_guesser as gender


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

        # Add quote tweet context to main tweet
        if tweet.get('is_quote', False):
            tweet_text += " " + tweet.get('qt_text', '')
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
    return find_matches(data, host_patterns, extract_function=extract_person_names,
                        context=awards, context_function=host_context)


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
    
