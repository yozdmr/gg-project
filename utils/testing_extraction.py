# Imports
import re
import time
import json
from collections import defaultdict
from utils.helpers.patterns import winning_patterns, host_patterns, award_patterns
from utils.helpers.text_matching import merge_similar_entries, extract_person_names, extract_awards


# Load tweets
def load_data(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return None


### DATA PROCESSING FUNCTIONS ###

def identify_matches(data, patterns, extract_function, n=5, \
        additional_context=None, additional_context_function=None):

    # both should be specified at the same time
    if (additional_context and not additional_context_function) or \
            (not additional_context and additional_context_function):
        raise ValueError("Must provide both additional_context and additional_context_function")

    matches = defaultdict(int)    
    for tweet in data:
        tweet_text = tweet.get('text', '')

        if additional_context:
            tweet_text += " " + additional_context

        # check if tweet contains pattern context
        has_pattern_context = any(re.search(pattern, tweet_text, re.IGNORECASE) 
                                for pattern in patterns)
        
        if has_pattern_context:
            # extract names using spaCy
            person_names = extract_function(tweet_text)
            for name in person_names:
                matches[name] += 1
    
    # merge similar entries
    merged_matches = merge_similar_entries(matches)
    
    # return top n matches
    top_n_matches = sorted(merged_matches.items(), key=lambda x: x[1], reverse=True)[:n]
    return dict(top_n_matches)


# Sample process tweets
def process_tweets(data):
    N = 10

    print("getting awards...")
    awards = identify_matches(data, award_patterns, extract_awards, n=21)

    # Next steps:
    #   pass awards as context to winners and hosts
    #     this will involve figuring hout how many awards to pass (how reliable are the award names?)
    #   for winners, filter tweets by award name, and find winners from filtered list
    #       then match list of winner candidates to award name
    #   for hosts, exclude all tweets that mention a specific award (this means person is presenter)
    #       then find hosts from remaining tweets
    print("getting winners...")
    winners = identify_matches(data, winning_patterns, extract_person_names, n=N)
    print("getting hosts...")
    hosts = identify_matches(data, host_patterns, extract_person_names, n=N)

    return winners, hosts, awards
        


if __name__ == "__main__":
    data_file = 'gg2013.json'

    # Load the main data file
    gg_data = load_data(data_file)
    if gg_data:
        print(f"Loaded {len(gg_data)} items from gg2013.json")

    # Measure time taken for process_tweets
    start_time = time.time()
    winners, hosts, awards = process_tweets(gg_data)
    end_time = time.time()
    print(f"Process took {end_time-start_time:.2f} seconds")

    # Print matches
    print("\n" + "="*50)
    print("WINNERS:")
    print("="*50)
    for match, count in winners.items():
        print(f"{match}: {count}")
    print("\n" + "="*50)
    print("HOSTS:")
    print("="*50)
    for match, count in hosts.items():
        print(f"{match}: {count}")
    print("\n" + "="*50)
    print("AWARDS:")
    print("="*50)
    for match, count in awards.items():
        print(f"{match}: {count}")
    
