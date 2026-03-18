#!/usr/bin/env python3
"""
orality_server.py — web interface for the orality analyzer.

Usage:
    python3 orality_server.py          # opens http://localhost:8000
    python3 orality_server.py 9090     # custom port

Expects index.html and app.js in the same directory.
Dependencies: stanza, cmudict
"""

import json
import re
import statistics
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import cmudict as _cmudict_pkg
import stanza

STATIC_DIR = Path(__file__).parent.parent / "web"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}

# ---------------------------------------------------------------------------
# Lazy stanza loading
# ---------------------------------------------------------------------------

nlp = None


def get_nlp():
    global nlp
    if nlp is not None:
        return nlp
    try:
        nlp = stanza.Pipeline("en", processors="tokenize,pos", verbose=False)
    except Exception:
        stanza.download("en", processors="tokenize,pos", verbose=False)
        nlp = stanza.Pipeline("en", processors="tokenize,pos", verbose=False)
    return nlp


# ---------------------------------------------------------------------------
# CMU dict + rule-based syllable counting
# ---------------------------------------------------------------------------

_cmu = _cmudict_pkg.dict()


VOWELS = set("aeiouy")


def _count_syllables_rule(word: str) -> int:
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


def count_syllables(word: str) -> int:
    clean = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not clean:
        return 0
    if clean in _cmu:
        return sum(1 for ph in _cmu[clean][0] if ph[-1].isdigit())
    return _count_syllables_rule(word)


# ---------------------------------------------------------------------------
# POS classification & contraction detection
# ---------------------------------------------------------------------------

CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"}

CONTRACTION_RE = re.compile(
    r"(?i)\b("
    r"\w+'t|\w+'re|\w+'ve|\w+'ll|\w+'d|\w+'m|\w+'s|let's"
    r"|gonna|wanna|gotta|kinda|sorta|coulda|shoulda|woulda"
    r")\b"
)

THRESH_LONG = 30
THRESH_DENSE = 0.55
THRESH_SYLLABLE = 1.8
THRESH_SUBORD_HEAVY = 2


# ---------------------------------------------------------------------------
# Analysis (mirrors orality.py exactly)
# ---------------------------------------------------------------------------


def analyse_sentence(sent) -> dict | None:
    words = [w for w in sent.words if w.text.isalpha()]
    if not words:
        return None

    n = len(words)
    syllables = sum(count_syllables(w.text) for w in words)
    syl_per_word = syllables / n

    content = sum(1 for w in words if w.upos in CONTENT_POS)
    lex_density = content / n

    coord = sum(1 for w in words if w.upos == "CCONJ")
    subord = sum(1 for w in words if w.upos == "SCONJ")
    contractions = len(CONTRACTION_RE.findall(sent.text))

    flesch = max(0.0, min(100.0, 206.835 - 1.015 * n - 84.6 * syl_per_word))

    flags = []
    if n > THRESH_LONG:
        flags.append({"type": "long", "label": f"Long sentence ({n} words)"})
    if lex_density > THRESH_DENSE:
        flags.append({"type": "dense", "label": f"Dense ({lex_density:.0%} content words)"})
    if syl_per_word > THRESH_SYLLABLE:
        flags.append({"type": "hard", "label": f"Hard words ({syl_per_word:.2f} syl/word)"})
    if subord >= THRESH_SUBORD_HEAVY and coord == 0:
        flags.append({"type": "subord", "label": f"Subordination-heavy ({subord} subord, 0 coord)"})

    return {
        "text": sent.text,
        "words": n,
        "sylPerWord": round(syl_per_word, 3),
        "lexDensity": round(lex_density, 3),
        "flesch": round(flesch, 1),
        "coord": coord,
        "subord": subord,
        "contractions": contractions,
        "flags": flags,
    }


def analyse(text: str) -> dict | None:
    doc = get_nlp()(text)

    sent_lengths = []
    sent_syllables = []
    all_upos = []
    coord_count = 0
    subord_count = 0
    contraction_count = 0
    details = []

    for sent in doc.sentences:
        info = analyse_sentence(sent)
        if not info:
            continue
        # Character offsets so the frontend can preserve inter-sentence gaps
        info["startChar"] = sent.tokens[0].start_char
        info["endChar"] = sent.tokens[-1].end_char
        details.append(info)
        n = info["words"]
        sent_lengths.append(n)
        sent_syllables.append(round(info["sylPerWord"] * n))
        contraction_count += info["contractions"]

        for w in sent.words:
            if not w.text.isalpha():
                continue
            all_upos.append(w.upos)
            if w.upos == "CCONJ":
                coord_count += 1
            elif w.upos == "SCONJ":
                subord_count += 1

    if not sent_lengths:
        return None

    total_words = sum(sent_lengths)
    total_syllables = sum(sent_syllables)
    mean_sl = statistics.mean(sent_lengths)
    std_sl = statistics.pstdev(sent_lengths) if len(sent_lengths) > 1 else 0.0
    syl_pw = total_syllables / total_words if total_words else 0
    flesch = max(0.0, min(100.0, 206.835 - 1.015 * mean_sl - 84.6 * syl_pw))

    content_words = sum(1 for u in all_upos if u in CONTENT_POS)
    lex_density = content_words / total_words if total_words else 0

    total_conj = coord_count + subord_count
    coord_ratio = coord_count / total_conj if total_conj else 0.5

    long_sents = sum(1 for l in sent_lengths if l > 30)
    long_ratio = long_sents / len(sent_lengths)
    contraction_ratio = contraction_count / total_words if total_words else 0

    c = {}
    c["flesch"] = max(0.0, min(1.0, (flesch - 30) / 60))
    c["sent_length"] = max(0.0, min(1.0, (30 - mean_sl) / 22))
    c["sent_variety"] = max(0.0, min(1.0, std_sl / 15))
    c["lexical_density"] = max(0.0, min(1.0, (0.6 - lex_density) / 0.25))
    c["coordination"] = max(0.0, min(1.0, (coord_ratio - 0.3) / 0.5))
    c["long_sents"] = max(0.0, min(1.0, 1.0 - long_ratio / 0.3))
    c["contractions"] = max(0.0, min(1.0, contraction_ratio / 0.06))

    weights = {
        "flesch": 0.18, "sent_length": 0.22, "sent_variety": 0.08,
        "lexical_density": 0.18, "coordination": 0.12, "long_sents": 0.10,
        "contractions": 0.12,
    }
    score = sum(c[k] * weights[k] for k in c) * 100

    label = (
        "Very oral" if score >= 80 else
        "Mostly oral" if score >= 65 else
        "Mixed" if score >= 50 else
        "Mostly written" if score >= 35 else
        "Very written"
    )

    return {
        "score": round(score, 1),
        "label": label,
        "originalText": text,
        "components": {k: round(v, 3) for k, v in c.items()},
        "metrics": {
            "sentences": len(sent_lengths),
            "words": total_words,
            "meanSentLen": round(mean_sl, 1),
            "stdSentLen": round(std_sl, 1),
            "sylPerWord": round(syl_pw, 2),
            "flesch": round(flesch, 1),
            "lexDensity": round(lex_density, 3),
            "coordRatio": round(coord_ratio, 2),
            "coordCount": coord_count,
            "subordCount": subord_count,
            "longRatio": round(long_ratio, 3),
            "contractionRatio": round(contraction_ratio, 4),
            "contractionCount": contraction_count,
        },
        "details": details,
    }


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.lstrip("/")
        if path == "" or path == "index.html":
            self._serve_file("index.html")
        elif path == "app.js":
            self._serve_file("app.js")
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/analyse":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        text = body.get("text", "").strip()

        if not text:
            self._json({"error": "No text provided."})
            return

        result = analyse(text)
        if not result:
            self._json({"error": "Couldn't parse any sentences."})
            return

        self._json(result)

    def _serve_file(self, name):
        filepath = STATIC_DIR / name
        if not filepath.exists():
            self.send_error(404, f"{name} not found in {STATIC_DIR}")
            return
        content = filepath.read_bytes()
        mime = MIME.get(filepath.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, obj):
        payload = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {args[0]}\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print("Loading stanza model…")
    get_nlp()
    print(f"Ready — opening http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    main()