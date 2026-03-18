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
import re
import statistics
import sys
from pathlib import Path

import stanza

# Download the English model on first run (tokenize, POS).
# Subsequent runs use the cached model.
stanza.download("en", processors="tokenize,pos", verbose=False)
nlp = stanza.Pipeline("en", processors="tokenize,pos", verbose=False)

# ---------------------------------------------------------------------------
# Syllable counting (stanza doesn't provide this — keep the rule-based counter)
# ---------------------------------------------------------------------------

VOWELS = set("aeiouy")


def count_syllables(word: str) -> int:
    word = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    word = re.sub(r"(?<=[aeiou])es$", "e", word)
    word = re.sub(r"(?<=[^aeiou])e$", "", word)

    count = len(re.findall(r"[aeiouy]+", word))

    if word.endswith("le") and len(word) > 2 and word[-3] not in VOWELS:
        count += 1
    if word.endswith("ed") and len(word) > 2 and word[-3] not in VOWELS:
        count -= 1

    return max(1, count)


# ---------------------------------------------------------------------------
# POS-based classification (Universal POS tags from stanza)
# ---------------------------------------------------------------------------

CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"}


def is_content_word(upos: str) -> bool:
    return upos in CONTENT_POS


# ---------------------------------------------------------------------------
# Per-sentence analysis
# ---------------------------------------------------------------------------

# Thresholds for flagging sentences
THRESH_LONG = 30          # words — sentences longer than this are "long"
THRESH_DENSE = 0.55       # lexical density above this is "dense"
THRESH_SYLLABLE = 1.8     # avg syllables/word above this is "hard"
THRESH_SUBORD_HEAVY = 2   # subordinators with 0 coordinators = flag


def analyse_sentence(sent) -> dict:
    """Analyse a single stanza Sentence and return per-sentence metrics."""
    words = [w for w in sent.words if w.text.isalpha()]
    if not words:
        return {}

    n = len(words)
    syllables = sum(count_syllables(w.text) for w in words)
    syl_per_word = syllables / n if n else 0

    content = sum(1 for w in words if is_content_word(w.upos))
    lex_density = content / n if n else 0

    coord = sum(1 for w in words if w.upos == "CCONJ")
    subord = sum(1 for w in words if w.upos == "SCONJ")

    flesch = 206.835 - 1.015 * n - 84.6 * syl_per_word
    flesch = max(0.0, min(100.0, flesch))

    # Build list of flags for this sentence
    flags = []
    if n > THRESH_LONG:
        flags.append(f"long ({n} words)")
    if lex_density > THRESH_DENSE:
        flags.append(f"dense (lex {lex_density:.0%})")
    if syl_per_word > THRESH_SYLLABLE:
        flags.append(f"hard words ({syl_per_word:.2f} syl/w)")
    if subord >= THRESH_SUBORD_HEAVY and coord == 0:
        flags.append(f"subordination-heavy ({subord} subord, 0 coord)")

    # Reconstruct the sentence text from tokens
    text = sent.text

    return {
        "text": text,
        "words": n,
        "syllables_per_word": syl_per_word,
        "lexical_density": lex_density,
        "flesch": flesch,
        "coord": coord,
        "subord": subord,
        "flags": flags,
    }


# ---------------------------------------------------------------------------
# Document-level analysis
# ---------------------------------------------------------------------------


def flesch_reading_ease(words_per_sent: float, syllables_per_word: float) -> float:
    return 206.835 - 1.015 * words_per_sent - 84.6 * syllables_per_word


def analyse(text: str) -> dict:
    doc = nlp(text)

    sent_lengths = []
    sent_syllables = []
    all_upos = []
    coord_count = 0
    subord_count = 0
    sent_details = []

    for sent in doc.sentences:
        info = analyse_sentence(sent)
        if not info:
            continue

        sent_details.append(info)
        n = info["words"]
        sent_lengths.append(n)
        sent_syllables.append(round(info["syllables_per_word"] * n))

        for w in sent.words:
            if not w.text.isalpha():
                continue
            all_upos.append(w.upos)
            if w.upos == "CCONJ":
                coord_count += 1
            elif w.upos == "SCONJ":
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

    content_words = sum(1 for upos in all_upos if is_content_word(upos))
    lexical_density = content_words / total_words if total_words else 0

    total_conj = coord_count + subord_count
    coord_ratio = coord_count / total_conj if total_conj else 0.5

    long_sents = sum(1 for length in sent_lengths if length > 30)
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
        "sent_details": sent_details,
    }


# ---------------------------------------------------------------------------
# Composite orality score
# ---------------------------------------------------------------------------


def orality_score(m: dict) -> tuple[float, dict[str, float]]:
    components = {}

    # Flesch: 0–100, higher = easier. Map [30, 90] → [0, 1]
    components["flesch"] = max(0.0, min(1.0, (m["flesch"] - 30) / 60))

    # Mean sentence length: Map [30, 8] → [0, 1] (inverted)
    components["sent_length"] = max(0.0, min(1.0, (30 - m["mean_sent_len"]) / 22))

    # Sentence length std dev: Map [0, 8] → [0, 1]
    components["sent_variety"] = max(0.0, min(1.0, m["std_sent_len"] / 8))

    # Lexical density: Map [0.6, 0.35] → [0, 1] (inverted)
    components["lexical_density"] = max(
        0.0, min(1.0, (0.6 - m["lexical_density"]) / 0.25)
    )

    # Coordination ratio: Map [0.3, 0.8] → [0, 1]
    components["coordination"] = max(0.0, min(1.0, (m["coord_ratio"] - 0.3) / 0.5))

    # Long sentence ratio: Map [0, 0.3] → [1, 0] (inverted)
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

MAX_PREVIEW = 70  # max chars to show for sentence previews


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


def truncate(text: str, maxlen: int = MAX_PREVIEW) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= maxlen:
        return text
    return text[: maxlen - 1] + "…"


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

    # Per-sentence diagnostics
    flagged = [
        (i, s) for i, s in enumerate(m["sent_details"], 1) if s["flags"]
    ]
    if flagged:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"  FLAGGED SENTENCES   ({len(flagged)} of {m['sentences']})")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        for num, s in flagged:
            lines.append(f"  [{num}] {truncate(s['text'])}")
            lines.append(f"       ⚑ {', '.join(s['flags'])}")
            lines.append("")
    else:
        lines.append("  No sentences flagged — nice work!")
        lines.append("")

    if verbose:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("  Raw metrics")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
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
