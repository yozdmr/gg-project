# Imports
import json
import spacy


# Load spaCy language model
nlp = spacy.load("en_core_web_sm")

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


# Sample process tweets
def process_tweets(data):
    for tweet in data:
        doc = nlp(tweet['text'])
        


if __name__ == "__main__":
    data_file = 'gg2013.json'

    # Load the main data file
    gg_data = load_data(data_file)
    if gg_data:
        print(f"Loaded {len(gg_data)} items from gg2013.json")

    # Maybe use multiprocessing in future for faster speeds?

    
