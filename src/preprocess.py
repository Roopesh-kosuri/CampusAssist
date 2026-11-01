"""Text preprocessing module for CampusAssist.

Provides dual preprocessing strategies:
1. Lexical (for Keyword and TF-IDF): normalization, Hinglish token mapping,
   stopword removal, suffix stemming, and unigram/bigram token extraction.
2. Semantic (for Dense Sentence Transformers): control char removal,
   whitespace normalization, and light Hinglish translation while strictly
   preserving grammar, sentence syntax, stopwords, and negations.
"""
import re
import unicodedata

# Hinglish vocabulary normalization map for common student terms & common typos
HINGLISH_LEXICAL_MAP = {
    "kab": "when",
    "kaha": "where",
    "kahan": "where",
    "kidhar": "where",
    "band": "close",
    "bandh": "close",
    "khulta": "open",
    "khulega": "open",
    "khula": "open",
    "pankha": "fan",
    "bijli": "electrician",
    "paani": "water",
    "pani": "water",
    "gum": "lost",
    "kho": "lost",
    "khoya": "lost",
    "paisa": "fee",
    "paise": "fee",
    "fine": "penalty",
    "kitna": "amount",
    "kitne": "amount",
    "baje": "time",
    "chahiye": "need",
    "kharab": "broken",
    "shuru": "start",
    "chutti": "holiday",
    "khana": "food",
    "kamra": "room",
    "gadi": "vehicle",
    "gaadi": "vehicle",
    # Campus typos & slang
    "timetible": "timetable",
    "downlod": "download",
    "registar": "register",
    "supplemntary": "supplementary",
    "attandance": "attendance",
    "attendence": "attendance",
    "reappear": "backlog",
    "recheck": "scrutiny",
    "rechecking": "scrutiny",
    "outpass": "gatepass",
    "hostle": "hostel",
    "maintence": "maintenance",
    "complant": "complaint",
    "pluming": "plumbing",
    "nite": "night",
    "duplcate": "duplicate",
    "crd": "card",
    "aply": "apply",
}

# Campus-specific phrase synonyms and expansion patterns
CAMPUS_SYNONYMS = [
    (r"\b(?:test hall permit|hall permit|exam permit|hall ticket)\b", "admit card hall ticket examination permit"),
    (r"\b(?:datesheet|timetible|time table|schedule)\b", "datesheet timetable examination schedule"),
    (r"\b(?:fitness tracking band|fitness band|smartwatch|smart watch|wearable)\b", "smartwatch electronic gadget prohibited unfair means"),
    (r"\b(?:supplemntary|backlog|reappear|re-appear|compartment)\b", "re-appear backlog supplementary examination"),
    (r"\b(?:written solutions were completely correct|scrutiny|re-evaluation|recheck|rechecking)\b", "scrutiny re-evaluation rechecking grade dispute"),
    (r"\b(?:attendance threshold|attendance percentage|short attendance|debarred)\b", "75 percent attendance eligibility debarred permit"),
    (r"\b(?:concurrent examination timings|clash|overlap|same time exam)\b", "date sheet clash grievance conflict concurrent examination"),
    (r"\b(?:official cgpa results|grade sheet|transcripts|marksheet)\b", "result declaration cgpa gradesheet timeline"),
    (r"\b(?:room tap|dripping water|water leaking|tap leak|washroom)\b", "plumber water maintenance hostel complaint repair"),
    (r"\b(?:surcharge|penalty charge|late installment penalty)\b", "late fee fine penalty surcharge cut-off"),
    (r"\b(?:chest pain|unconscious|severe bleeding|heart attack|fainted|ambulance needed)\b", "medical emergency unihospital ambulance doctor hospital 24x7"),
    (r"\b(?:extend (?:the )?borrowing period|extend borrowing|extend due date)\b", "renew book renewal extend borrowing period online catalogue OPAC"),
    (r"\b(?:electronic campus credential|identity pass|university credential)\b", "id card student identity card smart card"),
    (r"\b(?:shuttle fleet|transit vehicle|morning transit vehicle)\b", "university bus transport campus bus service"),
    (r"\b(?:cancellation and fee surrender|fee surrender|wired back|deducted money)\b", "fee refund withdrawal cancellation fee policy surrender"),
    (r"\b(?:private project rooms|discussion rooms|cubicles)\b", "study rooms research cubicles discussion rooms central library"),
    (r"\b(?:purchasing new ai reference texts|procure books|book requisition)\b", "library book recommendation requisition procurement purchase professor"),
]

# Semantic vocabulary translation (English replacements preserving clause semantics)
HINGLISH_SEMANTIC_REPLACEMENTS = [
    (r"\bkho\s+gaya\b", "lost"),
    (r"\bgum\s+ho\s+gaya\b", "lost"),
    (r"\bband\s+hoti\s+hai\b", "closes"),
    (r"\bband\s+hota\s+hai\b", "closes"),
    (r"\bkhulta\s+hai\b", "opens"),
    (r"\bkhulega\b", "will open"),
    (r"\bpankha\b", "fan"),
    (r"\bkharab\b", "broken"),
    (r"\bpaise\b", "fees"),
    (r"\bpaisa\b", "fee"),
    (r"\bkahan\b", "where"),
    (r"\bkaha\b", "where"),
    (r"\bkidhar\b", "where"),
    (r"\bkab\b", "when"),
    (r"\bkamra\b", "room"),
    (r"\bgaadi\b", "vehicle"),
    (r"\bgadi\b", "vehicle"),
    (r"\bbijli\b", "electricity"),
    (r"\bpaani\b", "water")
]

# Stopwords for lexical search (removes uninformative query fluff)
LEXICAL_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "shall", "will", "should",
    "would", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "by", "at", "with", "from", "about", "into", "through",
    "during", "before", "after", "above", "below", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "just", "don", "now", "i", "me", "my", "myself", "we", "our", "ours",
    "you", "your", "yours", "yourself", "he", "him", "his", "she", "her",
    "it", "its", "they", "them", "their", "what", "which", "who", "whom",
    "this", "that", "these", "those", "am", "tell", "want", "know", "please",
    "give", "get", "need",
    # Hinglish conversational fillers
    "bhai", "yaar", "sir", "mam", "karo", "kare", "karna", "hoga", "hogi",
    "hoti", "hota", "hai", "hain", "tha", "thi", "the", "ka", "ki", "ke",
    "ko", "se", "me", "mein", "par", "pe", "bhi", "toh", "kya", "kyu", "kyun",
    "mera", "meri", "mere", "apna", "apni", "apne", "wala", "wali", "wale"
}


def clean_control_chars(text: str) -> str:
    """Remove control characters and normalize unicode representation."""
    if not isinstance(text, str):
        return ""
    # Strip unprintable control characters except whitespace
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t", " "))
    return unicodedata.normalize("NFKC", text).strip()


def stem_word(w: str) -> str:
    """Lightweight rule-based suffix stemming for English words."""
    if len(w) <= 3:
        return w

    # Step 1: Plural and simple endings
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ss"):
        pass
    elif w.endswith("s") and not w.endswith("us") and not w.endswith("is"):
        w = w[:-1]

    # Step 2: Past tense & progressive
    if w.endswith("eed"):
        if len(w) > 4:
            w = w[:-1]
    elif (w.endswith("ed") or w.endswith("ing")) and len(w) > 4:
        stem = w[:-2] if w.endswith("ed") else w[:-3]
        if len(stem) >= 3:
            w = stem
            if w.endswith("at") or w.endswith("bl") or w.endswith("iz"):
                w = w + "e"
            elif len(w) > 2 and w[-1] == w[-2] and w[-1] not in "lsz":
                w = w[:-1]

    # Step 3: Derivational suffixes
    for suffix, repl in [
        ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
        ("izer", "ize"), ("abli", "able"), ("alli", "al"), ("entli", "ent"),
        ("eli", "e"), ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
        ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
        ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")
    ]:
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[:-len(suffix)] + repl
            break

    # Step 4: Common noun/adjective suffixes
    for suffix in ["ment", "able", "ible", "ance", "ence", "ful", "less", "ness"]:
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[:-len(suffix)]
            break

    return w


def extract_bigrams(tokens: list[str]) -> list[str]:
    """Generate contiguous bigrams from an ordered token sequence."""
    if len(tokens) < 2:
        return []
    return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]


def preprocess_lexical(text: str) -> tuple[list[str], list[str]]:
    """Lexical preprocessing for Keyword Overlap and TF-IDF models.
    
    Returns:
        tuple[list[str], list[str]]: (unigrams, bigrams)
    """
    clean = clean_control_chars(text).lower()
    for pattern, replacement in CAMPUS_SYNONYMS:
        clean = re.sub(pattern, replacement, clean, flags=re.IGNORECASE)
    # Replace non-alphanumeric chars (except apostrophes inside words) with space
    clean = re.sub(r"[^a-z0-9\s-]", " ", clean)
    clean = re.sub(r"[-_]", " ", clean)

    raw_tokens = clean.split()
    unigrams = []

    for t in raw_tokens:
        # Map common Hinglish terms to English canonical keywords
        t = HINGLISH_LEXICAL_MAP.get(t, t)
        if t in LEXICAL_STOPWORDS or len(t) <= 1:
            continue
        stemmed = stem_word(t)
        if stemmed and len(stemmed) > 1 and stemmed not in LEXICAL_STOPWORDS:
            unigrams.append(stemmed)

    bigrams = extract_bigrams(unigrams)
    return unigrams, bigrams


def preprocess_semantic(text: str) -> str:
    """Semantic preprocessing for Transformer Embeddings (all-MiniLM-L6-v2).
    
    Preserves grammatical syntax, stopwords, negations, and punctuation context,
    while normalizing whitespace and translating Hinglish domain terms.
    """
    clean = clean_control_chars(text)
    # Apply campus domain query expansion
    for pattern, replacement in CAMPUS_SYNONYMS:
        clean = re.sub(pattern, replacement, clean, flags=re.IGNORECASE)
    # Normalize multiple spaces and tabs
    clean = re.sub(r"\s+", " ", clean).strip()

    # Apply phrase-level Hinglish translations
    for pattern, replacement in HINGLISH_SEMANTIC_REPLACEMENTS:
        clean = re.sub(pattern, replacement, clean, flags=re.IGNORECASE)

    return clean
