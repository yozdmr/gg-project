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

award_patterns = {
    r'\b\swins\s\b': 1,
    r'\b\swinner of\s\b': 1,
    r'\b\sgoes to\s\b': 0,
    r'\b\sreceives\s\b': 1,
    r'\b\stakes home\s\b': 1,
    r'\b\sclaims\s\b': 1,
    r'\b\swon\s\b': 1,
    r'\b\ssecures\s\b': 1,
    r'\b\scaptures\s\b': 1,
    r'\b\snominated for\s\b': 1,
    # r'\b(([A-Z][a-z]*|[A-Z].)\s)+[Aa]ward\b': 0,  # Separate rule!!!
}