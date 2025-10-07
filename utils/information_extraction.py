# Imports
import re
import time
import json
from collections import defaultdict
from utils.helpers.patterns import winning_patterns, host_patterns, award_patterns
from utils.helpers.text_matching import merge_similar_entries, merge_similar_actors_awards, \
    extract_person_names, extract_awards
from utils.helpers.context_functions import award_winner_context, host_context


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

def identify_matches(data, patterns, extract_function, n=None, \
        additional_context=None, additional_context_function=None):

    # both should be specified at the same time
    if (additional_context and not additional_context_function) or \
            (not additional_context and additional_context_function):
        raise ValueError("Must provide both additional_context and additional_context_function")

    matches = defaultdict(int)    
    for tweet in data:
        # use best text field based on preprocessing
        if 'clean_text' in tweet:
            tweet_text = tweet.get('clean_text', '')
        elif 'text_no_tags' in tweet:
            tweet_text = tweet.get('text_no_tags', '')
        else:
            tweet_text = tweet.get('text', '')  # fallback for original format
        
        # NOTE: skip retweets for more accurate results (we can debate this)
        if tweet.get('is_retweet', False):
            continue
        
        # check if tweet contains pattern context
        has_pattern_context = any(re.search(pattern, tweet_text, re.IGNORECASE) 
                                for pattern in patterns)
        if has_pattern_context:
            extracted_items = additional_context_function(tweet_text, additional_context, extract_function) \
                if additional_context is not None \
                else extract_function(tweet_text)
            
            for item in extracted_items:
                matches[item] += 1
    
    # merge similar entries
    if all(isinstance(key, tuple) for key in matches):
        merged_matches = merge_similar_actors_awards(matches)
    else:
        merged_matches = merge_similar_entries(matches)
    
    # return top n matches
    if n is not None:
        top_n_matches = sorted(merged_matches.items(), key=lambda x: x[1], reverse=True)[:n]
        return dict(top_n_matches)
    else:
        return dict(merged_matches)


def process_tweets(data):
    print("getting awards...")
    awards = identify_matches(data, award_patterns, extract_awards)

    # TODO Next steps
    #   Getting name of award (e.g. "Golden Globes")
    #   Resolving trigger-happy merging of award names for winners
    #   Identifying nominees vs winners
    #   Identifying presenters vs hosts
    print("getting winners...")
    winners = identify_matches(data, winning_patterns, extract_person_names, \
        additional_context=awards, additional_context_function=award_winner_context)
    print("getting hosts...")
    hosts = identify_matches(data, host_patterns, extract_person_names, \
        additional_context=awards, additional_context_function=host_context)

    return winners, hosts, awards
        


if __name__ == "__main__":
    data_file = 'gg2013.json'
    n = 10

    # Load the main data file
    gg_data = load_data(data_file)
    if gg_data:
        print(f"Loaded {len(gg_data)} items from gg2013.json")

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
    print("\n" + "="*50)
    print("WINNERS:")
    print("="*50)
    for award, winners in new_winners.items():
        print(award)
        for winner, count in winners:
            if count < n:
                continue
            print(f"\t{winner}: {count}")
    print("\n" + "="*50)
    print("HOSTS:")
    print("="*50)
    for match, count in hosts.items():
        if count < n:
            continue
        print(f"{match}: {count}")
    print("\n" + "="*50)
    print("AWARDS:")
    print("="*50)
    for match, count in awards.items():
        if count < n:
            continue
        print(f"{match}: {count}")
    
