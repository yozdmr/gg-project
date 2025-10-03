import spacy
from collections import defaultdict
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm")
matcher = Matcher(nlp.vocab)

sample_texts = [
    # Direct Ballon d'Or winning texts
    "Ousmane Dembélé has won the 2024 Ballon d'Or in a stunning upset!",
    "The Ballon d'Or was awarded to Ousmane Dembélé for his exceptional season.",
    "Dembélé took home the prestigious Ballon d'Or trophy last night.",
    "After years of nominations, Ousmane Dembélé finally claimed the Ballon d'Or.",
    "The committee selected Ousmane Dembélé for the 2024 Ballon d'Or award.",
    
    # Contextual Ballon d'Or winning texts (no explicit "win")
    "Dembélé's name was called for the Ballon d'Or at the Paris ceremony.",
    "The French winger approached the stage to collect his golden ball.",
    "Ousmane Dembélé's emotional reaction upon hearing his name announced was unforgettable.",
    "After a standing ovation, Dembélé delivered his acceptance speech.",
    "The Ballon d'Or jury recognized Dembélé's outstanding performances this year.",
    "Dembélé's trophy collection grew with the most prestigious individual award.",
    
    # Podium finishers (legitimate but not winners)
    "Lamine Yamal finished second in the Ballon d'Or voting at just 17 years old.",
    "Lamine Yamal taking home second this year at just 18 is so impressive!",
    "Vitinha claimed third place in this year's Ballon d'Or rankings.",
    "The podium was completed by Yamal in second and Vitinha in third.",
    
    # Misleading/irrelevant Ballon d'Or ceremony texts
    "Streamer IShowSpeed absolutely killed it at the Ballon d'Or ceremony!",
    "Huge kudos to Lamine Yamal for making it this far at such a young age.",
    "Raphinha looked devastated after the Ballon d'Or results were announced.",
    "Mbappé's reaction to finishing outside the top 3 was captured on camera.",
    "Salah graciously congratulated the winner despite his own disappointment.",
    "The host did an amazing job keeping the energy high throughout the ceremony.",
    "Yamal's family was so proud watching him at the Ballon d'Or gala.",
    "The red carpet fashion at the Ballon d'Or was absolutely stunning this year.",
    "Vitinha's suit was one of the best looks of the Ballon d'Or night.",
    "The after-party following the Ballon d'Or ceremony went until 3 AM.",
    "Security was tight at the Ballon d'Or venue with so many stars present.",
    "The catering at the Ballon d'Or gala featured the finest French cuisine.",
    "Photographers couldn't get enough shots of Yamal posing with other nominees.",
    "The Ballon d'Or trophy display looked magnificent under the stage lights.",
    "Mbappé spent most of the ceremony chatting with other Real Madrid teammates.",
    "Raphinha posted on Instagram thanking fans for their Ballon d'Or support.",
    "The weather in Paris was perfect for the outdoor Ballon d'Or red carpet.",
    "Salah's interview after the ceremony showed his class and sportsmanship."
]

# Define patterns for key words
key_words = ['win', 'claim', 'finish', 'take']  # DEFINE THIS!


key_patterns = [[{"LEMMA": word}] for word in key_words]
matcher.add("KEY_WORDS", key_patterns)


# Process the text
winner_list = defaultdict(float)
award_list = defaultdict(float)
for text, doc in zip(sample_texts, nlp.pipe(sample_texts)):
    matches = matcher(doc)
    
    if matches:
        match_strings = [doc[start:end] for _, start, end in matches]
        print(f"\nText: {text}")
        print(f"Matches: {match_strings}")
        
        # Extract all proper nouns from the text
        proper_nouns = [token.text for token in doc if token.pos_ == "PROPN"]
        print(f"Proper nouns found: {proper_nouns}")
        
        # Add each proper noun to winner_list with score 1.0
        for noun in proper_nouns:
            winner_list[noun] += 1.0

# Print final winner scores
print("\n" + "="*50)
print("WINNER SCORES:")
print("="*50)
for winner, score in sorted(winner_list.items(), key=lambda x: x[1], reverse=True):
    print(f"{winner}: {score}")