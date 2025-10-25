# patterns for identifying nominees to awards
nominated_patterns = [
    r'\bnominated\s+(?:for|to)\b',
    r'\b(nominate|nominee)\b'
    r'\bup\s+for\b',
    r'\bin\s+the\s+running\s+for\b'
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
}

presenters_pattern = r"\b(present|presenter|presented|presenting|introduce|announce)\w*\b"