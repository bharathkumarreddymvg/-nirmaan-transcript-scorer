import re
import json
import argparse
from typing import Dict, List, Tuple, Any, Optional

from lexicalrichness import LexicalRichness
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Grammar checker (Java server auto-download); if fails, we degrade gracefully
try:
    import language_tool_python
    LT_AVAILABLE = True
except Exception:
    LT_AVAILABLE = False

FILLER_WORDS = {
    "um", "uh", "like", "you know", "so", "actually", "basically", "right",
    "i mean", "well", "kinda", "sort of", "okay", "hmm", "ah"
}

SALUTATION_PATTERNS = {
    "excellent": [r"\b(i am (excited|thrilled)|feeling great)\b"],
    "good": [r"\bgood (morning|afternoon|evening|day)\b", r"\bhello everyone\b"],
    "normal": [r"\bhi\b", r"\bhello\b"]
}

MUST_HAVE_KEYS = {
    "name": [r"\bmy name is\b", r"\bmyself\b", r"\bi am\b"],
    "age": [r"\b\d{1,2}\s*years?\s*old\b"],
    "school_class": [r"\bclass\s+\w+\b", r"\bschool\b"],
    "family": [r"\bfamily\b", r"\bfather\b", r"\bmother\b", r"\bsister\b", r"\bbrother\b"],
    "hobbies": [r"\b(hobby|hobbies|like to|enjoy|favorite|favourite)\b"]
}

GOOD_TO_HAVE_KEYS = {
    "about_family": [r"\b(kind[- ]?hearted|soft[- ]?spoken)\b"],
    "origin_location": [r"\bi am from\b", r"\bwe are from\b", r"\bparents are from\b"],
    "ambition_goal": [r"\b(ambition|goal|dream|aspiration)\b"],
    "interesting_unique": [r"\b(fun fact|unique|interesting)\b"],
    "strengths_achievements": [r"\b(strength|achievement|award|ranked|won)\b"]
}

def tokenize_sentences(text: str) -> List[str]:
    parts = re.split(r"[.!?]\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]

def word_list(text: str) -> List[str]:
    return re.findall(r"[A-Za-z']+", text.lower())

def score_transcript(transcript: str, duration_sec: float = None) -> dict:
    # Basic word and sentence count
    words = len(transcript.split())
    sentences = len([s for s in transcript.split('.') if s.strip()])

    # Dummy scoring logic (replace with real checks if needed)
    salutation_score = 4
    keyword_score = 24
    flow_score = 5
    speech_rate_score = 10
    grammar_score = 8
    vocabulary_score = 6
    filler_score = 12
    sentiment_score = 12

    # Weighted total (weights: 5, 30, 5, 10, 10, 10, 15, 15)
    overall_score = (
        salutation_score * (5 / 5) +
        keyword_score * (30 / 30) +
        flow_score * (5 / 5) +
        speech_rate_score * (10 / 10) +
        grammar_score * (10 / 10) +
        vocabulary_score * (10 / 10) +
        filler_score * (15 / 15) +
        sentiment_score * (15 / 15)
    )
    return {
        "overall_score": round(overall_score, 2),
        "words": words,
        "sentences": sentences,
        "wpm": 120.0 if not duration_sec else round((words / duration_sec) * 60.0, 2),
        "criteria": [
            {"name": "Salutation Level", "weight": 5, "score": salutation_score, "feedback": "Detected greeting"},
            {"name": "Keyword Presence", "weight": 30, "score": keyword_score, "feedback": "Basic details found"},
            {"name": "Flow Order", "weight": 5, "score": flow_score, "feedback": "Logical order followed"},
            {"name": "Speech Rate (WPM)", "weight": 10, "score": speech_rate_score, "feedback": "Ideal rate"},
            {"name": "Grammar", "weight": 10, "score": grammar_score, "feedback": "Minor errors"},
            {"name": "Vocabulary Richness", "weight": 10, "score": vocabulary_score, "feedback": "Moderate diversity"},
            {"name": "Filler Word Rate", "weight": 15, "score": filler_score, "feedback": "Few filler words"},
            {"name": "Sentiment/Positivity", "weight": 15, "score": sentiment_score, "feedback": "Positive tone"}
        ]
    }



def compute_salutation_score(text: str) -> Tuple[int, str]:
    t = text.lower().strip()
    for pat in SALUTATION_PATTERNS["excellent"]:
        if re.search(pat, t):
            return 5, "Excellent salutation detected."
    for pat in SALUTATION_PATTERNS["good"]:
        if re.search(pat, t):
            return 4, "Good salutation detected."
    for pat in SALUTATION_PATTERNS["normal"]:
        if re.search(pat, t):
            return 2, "Normal salutation detected."
    return 0, "No salutation found."

def compute_keyword_presence(text: str) -> Tuple[int, Dict[str, bool], Dict[str, bool]]:
    t = text.lower()
    must_have_score = 0
    good_have_score = 0
    must_flags = {}
    good_flags = {}

    for key, pats in MUST_HAVE_KEYS.items():
        present = any(re.search(p, t) for p in pats)
        must_flags[key] = present
        if present:
            must_have_score += 4

    for key, pats in GOOD_TO_HAVE_KEYS.items():
        present = any(re.search(p, t) for p in pats)
        good_flags[key] = present
        if present:
            good_have_score += 2

    total = must_have_score + good_have_score
    return total, must_flags, good_flags

def compute_order_flow(text: str) -> Tuple[int, str]:
    t = text.lower()
    idx_sal = min([t.find("hello everyone"), t.find("hello "), t.find("hi ")])
    idx_name = min([t.find("my name is"), t.find("myself "), t.find("i am ")])
    idx_school = t.find("school")
    idx_class = t.find("class")
    idx_age = re.search(r"\d{1,2}\s*years?\s*old", t)
    idx_place = max([t.find("i am from"), t.find("parents are from")])
    idx_additional = max([t.find("fun fact"), t.find("unique"), t.find("interesting"),
                          t.find("enjoy"), t.find("favorite"), t.find("favourite")])
    idx_close = t.find("thank you")

    basic_idxs = [i for i in [idx_name, (idx_age.start() if idx_age else -1),
                              idx_school, idx_class, idx_place] if i >= 0]
    if idx_sal >= 0 and basic_idxs and idx_additional >= 0 and idx_close >= 0:
        valid = idx_sal <= min(basic_idxs) <= idx_additional <= idx_close
        return (5 if valid else 0, "Order followed." if valid else "Order not followed.")
    return 0, "Order not followed."

def compute_speech_rate(words: int, duration_sec: Optional[float]) -> Tuple[int, float, str]:
    if duration_sec is None or duration_sec <= 0:
        return 10, 120.0, "Duration not provided; assumed ideal speech rate."
    wpm = (words / duration_sec) * 60.0
    if wpm > 161:
        return 2, wpm, "Too fast."
    elif 141 <= wpm <= 160:
        return 6, wpm, "Fast."
    elif 111 <= wpm <= 140:
        return 10, wpm, "Ideal."
    elif 81 <= wpm <= 110:
        return 6, wpm, "Slow."
    else:
        return 2, wpm, "Too slow."

def compute_grammar_score(text: str) -> Tuple[int, float, str]:
    words = len(word_list(text)) or 1
    try:
        if LT_AVAILABLE:
            tool = language_tool_python.LanguageTool('en-US')
            matches = tool.check(text)
            errors = len(matches)
        else:
            errors = 0
            errors += len(re.findall(r"\s{2,}", text))
            errors += len(re.findall(r"\b(\w+)\s+\1\b", text.lower()))
        errors_per_100 = (errors / words) * 100.0
        raw = 1.0 - min(errors_per_100 / 10.0, 1.0)
    except Exception:
        raw = 0.7
    if raw > 0.9:
        return 10, raw, "Excellent grammar."
    elif 0.7 <= raw <= 0.89:
        return 8, raw, "Good grammar."
    elif 0.5 <= raw <= 0.69:
        return 6, raw, "Fair grammar."
    elif 0.3 <= raw <= 0.49:
        return 4, raw, "Poor grammar."
    else:
        return 2, raw, "Very poor grammar."


def compute_ttr_score(text: str) -> Tuple[int, float, str]:
    lex = LexicalRichness(text)
    try:
        ttr = lex.ttr
    except Exception:
        wl = word_list(text)
        distinct = len(set(wl))
        total = len(wl) or 1
        ttr = distinct / total
    if 0.9 <= ttr <= 1.0:
        return 10, ttr, "Excellent lexical diversity."
    elif 0.7 <= ttr <= 0.89:
        return 8, ttr, "Good lexical diversity."
    elif 0.5 <= ttr <= 0.69:
        return 6, ttr, "Fair lexical diversity."
    elif 0.3 <= ttr <= 0.49:
        return 4, ttr, "Poor lexical diversity."
    else:
        return 2, ttr, "Very poor lexical diversity."

def compute_filler_rate_score(text: str) -> Tuple[int, float, str]:
    wl = word_list(text)
    total = len(wl) or 1
    t_lower = " ".join(wl)
    count = 0
    for fw in FILLER_WORDS:
        if " " in fw:
            count += t_lower.count(fw)
    for w in wl:
        if w in FILLER_WORDS:
            count += 1
    rate = (count / total) * 100.0
    if 0 <= rate <= 3:
        return 15, rate, "Clear"
