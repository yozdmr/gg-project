# Imports
import re
import time
import json
from collections import defaultdict
from utils.helpers.patterns import winning_patterns, host_patterns, award_patterns
from utils.helpers.text_matching import merge_similar_entries, extract_person_names, extract_awards


# Load tweets
def load_data(filepath):
    tweets = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                tweets.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return tweets


### DATA PROCESSING FUNCTIONS ###

def identify_matches(data, patterns, extract_function, n=5, \
        additional_context=None, additional_context_function=None):

    matches = defaultdict(int)
    for tweet in data:
        text = tweet.get('clean_text') or tweet.get('text_no_tags') or tweet.get('text', '')
        if tweet.get('is_retweet', False):
            continue
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            for item in extract_function(text):
                matches[item] += 1
    merged = merge_similar_entries(matches)
    return dict(sorted(merged.items(), key=lambda x: x[1], reverse=True)[:n])


def process_tweets(data):
    N = 10

    print("getting awards...")
    awards = identify_matches(data, award_patterns, extract_awards, n=21)
    award_categories = list(awards.keys())
    award_info = {award: {"Nominees": [], "Winner": None, "Presenters": []} for award in award_names}

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

    for award in award_categories:
        print(f"Processing award: {award}")
        # Filter tweets mentioning this award
        award_tweets = [tweet for tweet in data if 'clean_text' in tweet and award.lower() in tweet['clean_text']]
        if not award_tweets:
            continue
        winners_candidates = identify_matches(
            award_tweets, winning_patterns, extract_person_names, n=N
        )
        if winners_candidates:
            top_winner = max(winners_candidates, key=winners_candidates.get)
            award_info[award]["Winner"] = top_winner
        nominees_candidates = identify_matches(
            award_tweets, [], extract_person_names, n=N
        )
        if nominees_candidates:
            award_info[award]["Nominees"] = list(nominees_candidates.keys())
        presenters_candidates = identify_matches(
            award_tweets, [r"present", r"presents"], extract_person_names, n=N
        )
        if presenters_candidates:
            award_info[award]["Presenters"] = list(presenters_candidates.keys())

    # Extract hosts
    award_texts = set()
    for tweet in data:
        if 'clean_text' in tweet:
            award_texts.update([award.lower() for award in award_categories if award.lower() in tweet['clean_text']])

    host_tweets = [
        tweet for tweet in data
        if 'clean_text' in tweet and all(award.lower() not in tweet['clean_text'] for award in award_categories)
    ]
    print("Getting hosts...")
    hosts = identify_matches(host_tweets, host_patterns, extract_person_names, n=N)

    return winners, hosts, award_info
        


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
    
