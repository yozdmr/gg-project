# patterns for identifying winners of awards
winning_patterns = [
    r'\b(?:won|wins|claimed?)\b',
    r'\bwinner\s+(?:is|are|was|were)\b',
    r'\bawarded\s+to\b'
]

# patterns for identifying nominees to awards
nominated_patterns = [
    r'\bnominated\s+(?:for|to)\b',
    r'\b(nominate|nominee)\b'
    r'\bup\s+for\b',
    r'\bin\s+the\s+running\s+for\b'
]

# patterns for identifying hosts of awards
host_patterns = [
    r'\bhost\b',
    r'\bhosts\b',
    r'\bhosted\b',
    r'\bhosting\b'
]

# patterns for identifying awards
# award_patterns = [
    # Matches case "Best ___ - ___ ((or)? ___)?"
    # r'\b[Bb]est(?:\s+[A-Z][a-z]+)+(?:\s-\s[A-Z][a-z]+(?:\s(?:[Oo]r\s)?[A-Z][a-z]+)?)',

    # Matches case "Best ___ by an ___ in a ___ (- ___)?"
    #   Currently this is a subset of the below regex.
    # r'\b[Bb]est(?:\s+[A-Z][a-z]+)*\s[Bb]y [Aa]n\s[A-Z][a-z]+(?:\s[Ii]n [Aa]\s[A-Z][a-z]+(?:(\s|-)[A-Za-z]+)*)?(?:(?:\s-\s|\s[Ii]n [Aa]\s)[A-Z][a-z]+(?:\s[A-Za-z]+)?(?:\s[A-Z][a-z]+)?)?',

    # Matches case "Best ___ by an ___ (in a ___)* (- ___)?, (for|,\s|-)? --> between words"
    # r'\b[Bb]est(?:\s+[A-Z][a-z]+)*\s[Bb]y [Aa]n\s[A-Z][a-z]+(?:\s[Ii]n [Aa]\s[A-Z][a-z]+(?:(?:\s|-|,\s)(?:[Ii]n [Aa]|[Ff]?[Oo]r|[A-Z][a-z]+))*)?(?:\s-\s[A-Z][a-z]+(?:\s(?:[Oo]r\s)?[A-Z][a-z]+)?)?$',

    # Matches case "word [two-letter word that contains '.'] word word"
    # r'\b[A-Za-z]+\s[A-Za-z]\.\s[A-Za-z]+\s[A-Za-z]+\b',

    # Matches case "Best Word-Word (or|Word)+"
    # r'\b[Bb]est\s[A-Z][a-z]+-[A-Z][a-z]+(?:\s(?:[Ff]or|[Oo]r|[A-Z][a-z]+))+',

    # Matches case "Best Word Word Word"
    # r'\b([Ww]ins\s+)?[Bb]est(?:[\s,-]+[A-Za-z]+)*\b',
# ]

award_patterns = {
    r'\b\swins\s\b': 1,
    r'\b\swinner of\s\b': 1,
    r'\b\sgoes to\s\b': 0,
    r'\b\sreceives\s\b': 1,
    r'\b\stakes home\s\b': 1,
    r'\b\sclaims\s\b': 1,
    r'\b\swon\s\b': 1,
    r'\b\ssecures\s\b': 1,
    r'\b\scaptures\s\b': 1
}