import re

# extract winners only from tweets that mention specific award names
def award_winner_context(tweet_text, award_names, extract_function):
    award_winner_pairs = []
    
    for award_name in award_names:
        if re.search(award_name, tweet_text, re.IGNORECASE):
            # extract winners from tweet
            winners = extract_function(tweet_text)
            # pair each winner with this award
            for winner in winners:
                award_winner_pairs.append((award_name, winner))
    
    return award_winner_pairs

# extract hosts only from tweets that don't mention specific award names
def host_context(tweet_text, award_names, extract_function):
    # only check tweets that don't have an award name in it
    if not any(re.search(award_name, tweet_text, re.IGNORECASE) for award_name in award_names):
        # extract hosts from tweet
        hosts = extract_function(tweet_text)
        return hosts
    
    return []