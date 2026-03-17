#!/usr/bin/env python3
"""
orality.py — measures how natural a piece of writing is to say out loud.

Usage:
    python3 orality.py myfile.txt
    cat myfile.txt | python3 orality.py
    python3 orality.py --help

Metrics:
    • Flesch Reading Ease          — syllable/sentence complexity proxy
    • Mean sentence length         — shorter = more oral
    • Sentence length std dev      — variety = more oral
    • Lexical density              — content words / total words (lower = more oral)
    • Coordination ratio           — and/but/so vs. subordinators (higher = more oral)
    • Long-sentence ratio          — % of sentences over 30 words (lower = more oral)
    • Orality score                — composite 0–100
"""

import argparse
import math
import re
import statistics
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Syllable counting (Syl algorithm — no external deps)
# ---------------------------------------------------------------------------

VOWELS = set("aeiouyAEIOUY")


def count_syllables(word: str) -> int:
    word = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Strip common silent-e endings
    word = re.sub(r"(?<=[aeiou])es$", "e", word)
    word = re.sub(r"(?<=[^aeiou])e$", "", word)

    # Count vowel groups
    count = len(re.findall(r"[aeiouy]+", word))

    # Adjustments
    if word.endswith("le") and len(word) > 2 and word[-3] not in VOWELS:
        count += 1
    if word.endswith("ed") and len(word) > 2 and word[-3] not in VOWELS:
        count -= 1

    return max(1, count)


def syllable_count_sentence(words: list[str]) -> int:
    return sum(count_syllables(w) for w in words)


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"])")


def split_sentences(text: str) -> list[str]:
    # Protect common abbreviations before splitting
    text = re.sub(r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.", r"\1<DOT>", text)
    sents = SENT_SPLIT.split(text)
    return [s.replace("<DOT>", ".").strip() for s in sents if s.strip()]


def tokenise(sentence: str) -> list[str]:
    return re.findall(r"\b[a-zA-Z']+\b", sentence)


# ---------------------------------------------------------------------------
# Part-of-speech approximation (no tagger — rule-based word lists)
# ---------------------------------------------------------------------------

FUNCTION_WORDS = {
    # determiners
    "the",
    "a",
    "an",
    "this",
    "that",
    "these",
    "those",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "some",
    "any",
    "no",
    "every",
    "each",
    "both",
    "either",
    "neither",
    "all",
    "most",
    "many",
    "much",
    "few",
    "little",
    "more",
    "less",
    "other",
    "another",
    "such",
    "what",
    "which",
    "whose",
    # pronouns
    "i",
    "me",
    "we",
    "us",
    "you",
    "he",
    "him",
    "she",
    "they",
    "them",
    "it",
    "who",
    "whom",
    "whoever",
    "whatever",
    "one",
    "ones",
    "myself",
    "yourself",
    "himself",
    "herself",
    "itself",
    "ourselves",
    "themselves",
    # prepositions
    "in",
    "on",
    "at",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "from",
    "up",
    "down",
    "out",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
    "of",
    "as",
    "per",
    "via",
    "re",
    # coordinating conjunctions
    "and",
    "but",
    "or",
    "nor",
    "for",
    "yet",
    "so",
    # subordinating conjunctions
    "although",
    "though",
    "even",
    "because",
    "since",
    "unless",
    "until",
    "while",
    "whereas",
    "whether",
    "if",
    "than",
    "when",
    "where",
    "how",
    "that",
    "after",
    "before",
    "once",
    "as",
    "until",
    "till",
    "provided",
    "assuming",
    "given",
    "except",
    # auxiliaries & copulas
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "am",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "shall",
    "should",
    "may",
    "might",
    "must",
    "can",
    "could",
    "need",
    "dare",
    "ought",
    "used",
    # particles / misc
    "not",
    "n't",
    "to",
    "there",
    "here",
    "just",
    "also",
    "only",
    "even",
    "still",
    "already",
    "yet",
    "both",
    "either",
    "too",
    "very",
    "quite",
    "rather",
    "really",
    "just",
    "then",
    "now",
    "so",
    "well",
    "oh",
    "ah",
    "yes",
    "no",
    "hey",
    "please",
    "thank",
    "thanks",
}

COORD_CONJUNCTIONS = {"and", "but", "so", "or", "nor", "yet", "for"}

SUBORD_CONJUNCTIONS = {
    "although",
    "though",
    "because",
    "since",
    "unless",
    "until",
    "while",
    "whereas",
    "whether",
    "if",
    "whenever",
    "wherever",
    "however",
    "whatever",
    "whichever",
    "whoever",
    "after",
    "before",
    "once",
    "as",
    "till",
    "provided",
    "assuming",
    "given",
    "except",
    "insofar",
    "inasmuch",
    "notwithstanding",
}


def is_content_word(word: str) -> bool:
    return word.lower() not in FUNCTION_WORDS and len(word) > 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def flesch_reading_ease(words_per_sent: float, syllables_per_word: float) -> float:
    return 206.835 - 1.015 * words_per_sent - 84.6 * syllables_per_word


def analyse(text: str) -> dict:
    sentences = split_sentences(text)
    if not sentences:
        return {}

    sent_lengths = []  # word counts
    sent_syllables = []  # syllable counts
    all_words = []
    coord_count = 0
    subord_count = 0

    for sent in sentences:
        words = tokenise(sent)
        if not words:
            continue
        sent_lengths.append(len(words))
        sent_syllables.append(syllable_count_sentence(words))
        all_words.extend(w.lower() for w in words)

        for w in words:
            wl = w.lower()
            if wl in COORD_CONJUNCTIONS:
                coord_count += 1
            if wl in SUBORD_CONJUNCTIONS:
                subord_count += 1

    if not sent_lengths:
        return {}

    total_words = sum(sent_lengths)
    total_syllables = sum(sent_syllables)
    mean_sent_len = statistics.mean(sent_lengths)
    std_sent_len = statistics.pstdev(sent_lengths) if len(sent_lengths) > 1 else 0.0

    syllables_per_word = total_syllables / total_words if total_words else 0
    flesch = flesch_reading_ease(mean_sent_len, syllables_per_word)
    flesch = max(0.0, min(100.0, flesch))

    content_words = sum(1 for w in all_words if is_content_word(w))
    lexical_density = content_words / total_words if total_words else 0

    total_conj = coord_count + subord_count
    coord_ratio = coord_count / total_conj if total_conj else 0.5  # neutral if none

    long_sents = sum(1 for l in sent_lengths if l > 30)
    long_sent_ratio = long_sents / len(sent_lengths)

    return {
        "sentences": len(sent_lengths),
        "words": total_words,
        "mean_sent_len": mean_sent_len,
        "std_sent_len": std_sent_len,
        "syllables_per_word": syllables_per_word,
        "flesch": flesch,
        "lexical_density": lexical_density,
        "coord_ratio": coord_ratio,
        "coord_count": coord_count,
        "subord_count": subord_count,
        "long_sent_ratio": long_sent_ratio,
    }


# ---------------------------------------------------------------------------
# Composite orality score
# ---------------------------------------------------------------------------
#
# Each metric is normalised to 0–1 where 1 = most oral.
# Weights are subjective but calibrated to feel reasonable.
#


def orality_score(m: dict) -> tuple[float, dict[str, float]]:
    components = {}

    # Flesch: 0–100, higher = easier. Oral writing tends ≥ 60.
    # Map [30, 90] → [0, 1]
    components["flesch"] = max(0.0, min(1.0, (m["flesch"] - 30) / 60))

    # Mean sentence length: oral ≈ ≤15 words, written ≈ 25+
    # Map [30, 8] → [0, 1]  (inverted)
    components["sent_length"] = max(0.0, min(1.0, (30 - m["mean_sent_len"]) / 22))

    # Sentence length std dev: variety is oral. Map [0, 8] → [0, 1]
    components["sent_variety"] = max(0.0, min(1.0, m["std_sent_len"] / 8))

    # Lexical density: oral ≈ 0.35–0.45, written ≈ 0.55+
    # Map [0.6, 0.35] → [0, 1]  (inverted)
    components["lexical_density"] = max(
        0.0, min(1.0, (0.6 - m["lexical_density"]) / 0.25)
    )

    # Coordination ratio: higher = more oral. Map [0.3, 0.8] → [0, 1]
    components["coordination"] = max(0.0, min(1.0, (m["coord_ratio"] - 0.3) / 0.5))

    # Long sentence ratio: lower = more oral. Map [0, 0.3] → [1, 0]  (inverted)
    components["long_sents"] = max(0.0, min(1.0, 1.0 - m["long_sent_ratio"] / 0.3))

    weights = {
        "flesch": 0.20,
        "sent_length": 0.25,
        "sent_variety": 0.10,
        "lexical_density": 0.20,
        "coordination": 0.15,
        "long_sents": 0.10,
    }

    score = sum(components[k] * weights[k] for k in components) * 100
    return score, components


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def bar(value: float, width: int = 30) -> str:
    filled = round(value * width)
    return "█" * filled + "░" * (width - filled)


def score_label(score: float) -> str:
    if score >= 80:
        return "Very oral"
    if score >= 65:
        return "Mostly oral"
    if score >= 50:
        return "Mixed"
    if score >= 35:
        return "Mostly written"
    return "Very written"


def fmt_bar(label: str, value: float, lo: str, hi: str, width=24) -> str:
    b = bar(value, width)
    return f"  {label:<22} {b}  ({lo} ◀──▶ {hi})"


def render(m: dict, score: float, components: dict[str, float], verbose: bool) -> str:
    lines = []
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"  ORALITY SCORE   {score:.1f}/100   {score_label(score)}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    lines.append("  Component breakdown  (left = written, right = oral)")
    lines.append("")
    lines.append(fmt_bar("Readability (Flesch)", components["flesch"], "dense", "easy"))
    lines.append(fmt_bar("Sentence length", components["sent_length"], "long", "short"))
    lines.append(
        fmt_bar("Length variety", components["sent_variety"], "uniform", "varied")
    )
    lines.append(
        fmt_bar("Lexical density", components["lexical_density"], "high", "low")
    )
    lines.append(
        fmt_bar(
            "Coordination ratio",
            components["coordination"],
            "subordinated",
            "coordinated",
        )
    )
    lines.append(
        fmt_bar("Long sentence ratio", components["long_sents"], "many", "few")
    )
    lines.append("")

    if verbose:
        lines.append("  Raw metrics")
        lines.append(f"    Sentences              {m['sentences']}")
        lines.append(f"    Words                  {m['words']}")
        lines.append(f"    Mean sentence length   {m['mean_sent_len']:.1f} words")
        lines.append(f"    Sentence length σ      {m['std_sent_len']:.1f} words")
        lines.append(f"    Syllables per word     {m['syllables_per_word']:.2f}")
        lines.append(f"    Flesch Reading Ease    {m['flesch']:.1f}")
        lines.append(f"    Lexical density        {m['lexical_density']:.2f}")
        lines.append(f"    Coord conjunctions     {m['coord_count']}")
        lines.append(f"    Subord conjunctions    {m['subord_count']}")
        lines.append(f"    Coord ratio            {m['coord_ratio']:.2f}")
        lines.append(f"    Long sentences (>30w)  {m['long_sent_ratio'] * 100:.0f}%")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Measure how natural a piece of writing is to say out loud.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Text file to analyse (reads stdin if omitted)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show raw metric values"
    )
    args = parser.parse_args()

    if args.file:
        try:
            text = args.file.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        text = sys.stdin.read()

    text = text.strip()
    if not text:
        print("Error: no text to analyse.", file=sys.stderr)
        sys.exit(1)

    m = analyse(text)
    if not m:
        print("Error: couldn't parse any sentences from the input.", file=sys.stderr)
        sys.exit(1)

    score, components = orality_score(m)
    print(render(m, score, components, args.verbose))


if __name__ == "__main__":
    main()
