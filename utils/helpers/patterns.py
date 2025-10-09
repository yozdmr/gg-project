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
award_patterns = [
    r"\bBest\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*",
    r"\bOutstanding\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*",
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Award",
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Achievement|Choice|Prize)\b",
]