'''Version 0.5'''
import os
import json

# Import the information extraction module
from utils.information_extraction import process_tweets, load_data
from utils.preprocessing import preprocess_file_to_jsonl


# Year of the Golden Globes ceremony being analyzed
YEAR = "2013"

# Global variable for hardcoded award names
# This list is used by get_nominees(), get_winner(), and get_presenters() functions
# as the keys for their returned dictionaries
# Students should populate this list with the actual award categories for their year, to avoid cascading errors on outputs that depend on correctly extracting award names (e.g., nominees, presenters, winner)
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

NOMINEES = {
    "best screenplay - motion picture": [
        "zero dark thirty",
        "lincoln",
        "silver linings playbook",
        "argo"
    ],
    "best director - motion picture": [
        "kathryn bigelow",
        "ang lee",
        "steven spielberg",
        "quentin tarantino"
    ],
    "best performance by an actress in a television series - comedy or musical": [
        "zooey deschanel",
        "tina fey",
        "julia louis-dreyfus",
        "amy poehler"
    ],
    "best foreign language film": [
        "the intouchables",
        "kon tiki",
        "a royal affair",
        "rust and bone"
    ],
    "best performance by an actor in a supporting role in a motion picture": [
        "alan arkin",
        "leonardo dicaprio",
        "philip seymour hoffman",
        "tommy lee jones"
    ],
    "best performance by an actress in a supporting role in a series, mini-series or motion picture made for television": [
        "hayden panettiere",
        "archie panjabi",
        "sarah paulson",
        "sofia vergara"
    ],
    "best motion picture - comedy or musical": [
        "the best exotic marigold hotel",
        "moonrise kingdom",
        "salmon fishing in the yemen",
        "silver linings playbook"
    ],
    "best performance by an actress in a motion picture - comedy or musical": [
        "emily blunt",
        "judi dench",
        "maggie smith",
        "meryl streep"
    ],
    "best mini-series or motion picture made for television": [
        "the girl",
        "hatfields & mccoys",
        "the hour",
        "political animals"
    ],
    "best original score - motion picture": [
        "argo",
        "anna karenina",
        "cloud atlas",
        "lincoln"
    ],
    "best performance by an actress in a television series - drama": [
        "connie britton",
        "glenn close",
        "michelle dockery",
        "julianna margulies"
    ],
    "best performance by an actress in a motion picture - drama": [
        "marion cotillard",
        "sally field",
        "helen mirren",
        "naomi watts",
        "rachel weisz"
    ],
    "cecil b. demille award": [],
    "best performance by an actor in a motion picture - comedy or musical": [
        "jack black",
        "bradley cooper",
        "ewan mcgregor",
        "bill murray"
    ],
    "best motion picture - drama": [
        "django unchained",
        "life of pi",
        "lincoln",
        "zero dark thirty"
    ],
    "best performance by an actor in a supporting role in a series, mini-series or motion picture made for television": [
        "max greenfield",
        "danny huston",
        "mandy patinkin",
        "eric stonestreet"
    ],
    "best performance by an actress in a supporting role in a motion picture": [
        "amy adams",
        "sally field",
        "helen hunt",
        "nicole kidman"
    ],
    "best television series - drama": [
        "boardwalk empire",
        "breaking bad",
        "downton abbey (masterpiece)",
        "the newsroom"
    ],
    "best performance by an actor in a mini-series or motion picture made for television": [
        "benedict cumberbatch",
        "woody harrelson",
        "toby jones",
        "clive owen"
    ],
    "best performance by an actress in a mini-series or motion picture made for television": [
        "nicole kidman",
        "jessica lange",
        "sienna miller",
        "sigourney weaver"
    ],
    "best animated feature film": [
        "frankenweenie",
        "hotel transylvania",
        "rise of the guardians",
        "wreck-it ralph"
    ],
    "best original song - motion picture": [
        "act of valor",
        "stand up guys",
        "the hunger games",
        "les miserables"
    ],
    "best performance by an actor in a motion picture - drama": [
        "richard gere",
        "john hawkes",
        "joaquin phoenix",
        "denzel washington"
    ],
    "best television series - comedy or musical": [
        "the big bang theory",
        "episodes",
        "modern family",
        "smash"
    ],
    "best performance by an actor in a television series - drama": [
        "steve buscemi",
        "bryan cranston",
        "jeff daniels",
        "jon hamm"
    ],
    "best performance by an actor in a television series - comedy or musical": [
        "alec baldwin",
        "louis c.k.",
        "matt leblanc",
        "jim parsons"
    ]
}


def get_hosts(year):
    '''Returns the host(s) of the Golden Globes ceremony for the given year.
    
    Args:
        year (str): The year of the Golden Globes ceremony (e.g., "2013")
    
    Returns:
        list: A list of strings containing the host names. 
              Example: ["Seth Meyers"] or ["Tina Fey", "Amy Poehler"]
    
    Note:
        - Do NOT change the name of this function or what it returns
        - The function should return a list even if there's only one host
    '''
    # Your code here
    return hosts

def get_awards(year):
    '''Returns the list of award categories for the Golden Globes ceremony.
    
    Args:
        year (str): The year of the Golden Globes ceremony (e.g., "2013")
    
    Returns:
        list: A list of strings containing award category names.
              Example: ["Best Motion Picture - Drama", "Best Motion Picture - Musical or Comedy", 
                       "Best Performance by an Actor in a Motion Picture - Drama"]
    
    Note:
        - Do NOT change the name of this function or what it returns
        - Award names should be extracted from tweets, not hardcoded
        - The only hardcoded part allowed is the word "Best"
    '''
    
    return awards

def get_nominees(year):
    '''Returns the nominees for each award category.
    
    Args:
        year (str): The year of the Golden Globes ceremony (e.g., "2013")
    
    Returns:
        dict: A dictionary where keys are award category names and values are 
              lists of nominee strings.
              Example: {
                  "Best Motion Picture - Drama": [
                      "Three Billboards Outside Ebbing, Missouri",
                      "Call Me by Your Name", 
                      "Dunkirk",
                      "The Post",
                      "The Shape of Water"
                  ],
                  "Best Motion Picture - Musical or Comedy": [
                      "Lady Bird",
                      "The Disaster Artist",
                      "Get Out",
                      "The Greatest Showman",
                      "I, Tonya"
                  ]
              }
    
    Note:
        - Do NOT change the name of this function or what it returns
        - Use the hardcoded award names as keys (from the global AWARD_NAMES list)
        - Each value should be a list of strings, even if there's only one nominee
    '''
    # Your code here
    return nominees

def get_winner(year):
    '''Returns the winner for each award category.
    
    Args:
        year (str): The year of the Golden Globes ceremony (e.g., "2013")
    
    Returns:
        dict: A dictionary where keys are award category names and values are 
              single winner strings.
              Example: {
                  "Best Motion Picture - Drama": "Three Billboards Outside Ebbing, Missouri",
                  "Best Motion Picture - Musical or Comedy": "Lady Bird",
                  "Best Performance by an Actor in a Motion Picture - Drama": "Gary Oldman"
              }
    
    Note:
        - Do NOT change the name of this function or what it returns
        - Use the hardcoded award names as keys (from the global AWARD_NAMES list)
        - Each value should be a single string (the winner's name)
    '''
    # Your code here
    return winners

def get_presenters(year):
    '''Returns the presenters for each award category.
    
    Args:
        year (str): The year of the Golden Globes ceremony (e.g., "2013")
    
    Returns:
        dict: A dictionary where keys are award category names and values are 
              lists of presenter strings.
              Example: {
                  "Best Motion Picture - Drama": ["Barbra Streisand"],
                  "Best Motion Picture - Musical or Comedy": ["Alicia Vikander", "Michael Keaton"],
                  "Best Performance by an Actor in a Motion Picture - Drama": ["Emma Stone"]
              }
    
    Note:
        - Do NOT change the name of this function or what it returns
        - Use the hardcoded award names as keys (from the global AWARD_NAMES list)
        - Each value should be a list of strings, even if there's only one presenter
    '''
    # Your code here
    return presenters

def pre_ceremony():
    '''Pre-processes and loads data for the Golden Globes analysis.
    
    This function should be called before any other functions to:
    - Load and process the tweet data from gg2013.json
    - Download required models (e.g., spaCy models)
    - Perform any initial data cleaning or preprocessing
    - Store processed data in files or database for later use
    
    This is the first function the TA will run when grading.
    
    Note:
        - Do NOT change the name of this function or what it returns
        - This function should handle all one-time setup tasks
        - Print progress messages to help with debugging
    '''
    print("Starting pre-ceremony processing...")
    
    # Check if preprocessed file already exists
    preprocessed_file = 'gg2013_preprocessed.jsonl'
    original_file = 'gg2013.json'
    
    if os.path.exists(preprocessed_file):
        print(f"Preprocessed file {preprocessed_file} already exists. Skipping preprocessing.")
    else:
        if not os.path.exists(original_file):
            print(f"Error: Original data file {original_file} not found!")
            return
        
        print(f"Preprocessing {original_file} to create {preprocessed_file}...")
        try:
            num_tweets = preprocess_file_to_jsonl(original_file, preprocessed_file)
            print(f"Successfully preprocessed {num_tweets} tweets to {preprocessed_file}")
        except Exception as e:
            print(f"Error during preprocessing: {e}")

    print("Pre-ceremony processing complete.")

def main():
    '''Main function that orchestrates the Golden Globes analysis.
    
    This function should:
    - Call pre_ceremony() to set up the environment
    - Run the main analysis pipeline
    - Generate and save results in the required JSON format
    - Print progress messages and final results
    
    Usage:
        - Command line: python gg_api.py
        - Python interpreter: import gg_api; gg_api.main()
    
    This is the second function the TA will run when grading.
    
    Note:
        - Do NOT change the name of this function or what it returns
        - This function should coordinate all the analysis steps
        - Make sure to handle errors gracefully
    '''
    print("Starting Golden Globes 2013 Analysis...")
    
    # Run pre-ceremony setup
    pre_ceremony()
    
    # Extract awards
    print("\nExtracting information...")

    # Load the preprocessed data
    data_file = 'gg2013_preprocessed.jsonl'
    gg_data = load_data(data_file)
    
    if not gg_data:
        print(f"Error: Could not load data from {data_file}")
        return []
    
    # Process tweets to extract awards, winners, and hosts
    winner_data, hosts, awards = process_tweets(gg_data)
    winners, winner_candidates = winner_data


    # Prepare output in the required JSON structure
    output = {
        "extracted_awards": {
            "awards": awards
        },
        "extracted_hosts": list(hosts.keys()) if isinstance(hosts, dict) else (hosts if isinstance(hosts, list) else [hosts]),
        "extracted_winners": {
            "winners": winners,
            "candidate_winners": [elem[0] for award, elems in winner_candidates.items() for elem in (elems[1:] if len(elems) > 1 else [])]
        },
        "extracted_nominees": {},    # TODO: Implement nominees extraction
        "extracted_presenters": {}   # TODO: Implement presenters extraction
    }

    # Save the output to a file
    with open('gg2013_extracted.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output


if __name__ == '__main__':
    main()
