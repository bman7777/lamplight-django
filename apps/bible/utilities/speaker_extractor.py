# pylint: disable=too-many-lines,duplicate-value,implicit-str-concat,missing-function-docstring,too-many-locals,too-many-branches,too-many-statements,too-many-return-statements,unused-argument,too-few-public-methods
"""Per-verse speaker extraction for NASB95 bible text.

Walks verses in order, tracking who is speaking inside each quoted span.
NASB95 re-opens every verse of a continuing speech with U+201C but only
closes with U+201D at the end of the speech — so we cannot rely on a
balance count and instead carry per-verse state forward.
"""

import re

OPEN_Q = "“"
CLOSE_Q = "”"
OPEN_SQ = "‘"
CLOSE_SQ = "’"
NESTED = "‹NESTED›"

_VERBS = (
    r"said|saying|says|say|spoke|speaks|"
    r"answered|answering|replied|replying|"
    r"asked|asking|told|telling|"
    r"cried\s+out|cried|crying|"
    r"declared|declaring|proclaimed|proclaiming|"
    r"commanded|commanding|"
    r"prayed|praying|prophesied|prophesying|"
    r"wrote|writing|written|sang|singing|"
    r"warned|exclaimed|shouted|announced|"
    r"called\s+out|called|calling"
)

_ROLES = (
    r"woman|man|serpent|king|queen|priest|prophet|prophets|"
    r"disciples|disciple|crowds|crowd|elders|elder|angel|angels|"
    r"people|son|daughter|father|mother|brothers|brother|sister|servant|"
    r"Pharisees|Sadducees|scribes|chief\s+priests|Jews|Gentiles|Philistines"
)

_SPECIAL = (
    r"LORD\s+God|LORD\s+of\s+hosts|LORD|"
    r"Lord\s+GOD|Lord\s+Jesus|Lord|God|"
    r"Jesus\s+Christ|Christ\s+Jesus|Jesus|Christ|"
    r"Holy\s+Spirit|Spirit|"
    r"angel\s+of\s+the\s+LORD|Son\s+of\s+Man|Son\s+of\s+God"
)

# Words that look like proper nouns when sentence-initial but aren't real
# subjects — and uppercase pronouns we want excluded from the generic
# proper-noun matcher so the explicit pronoun alternatives in _SUBJ fire
# instead. Used both as a regex-level negative lookahead (so finditer
# advances past them) and as a code-level safety check.
_STOP_WORDS = {
    "now",
    "then",
    "and",
    "so",
    "but",
    "for",
    "yet",
    "also",
    "or",
    "nor",
    "when",
    "while",
    "after",
    "before",
    "until",
    "if",
    "because",
    "since",
    "though",
    "although",
    "lest",
    "whether",
    "despite",
    "even",
    "behold",
    "indeed",
    "cursed",
    "blessed",
    "therefore",
    "moreover",
    "however",
    "thus",
    "hence",
    "as",
    "like",
    "both",
    "by",
    "in",
    "on",
    "of",
    "to",
    "from",
    "with",
    "at",
    "across",
    "around",
    "above",
    "below",
    "beyond",
    "behind",
    "beside",
    "between",
    "through",
    "throughout",
    "toward",
    "towards",
    "upon",
    "within",
    "without",
    "during",
    "against",
    "into",
    "onto",
    "off",
    "out",
    "down",
    "up",
    "over",
    "under",
    "near",
    "afterward",
    "meanwhile",
    "presently",
    "henceforth",
    "thereafter",
    "turning",
    "seeing",
    "hearing",
    "immediately",
    "instantly",
    # Common past-participle and gerund clause-openers (NASB narrative style).
    "moved",
    "filled",
    "struck",
    "raised",
    "lifted",
    "stretched",
    "opened",
    "gathered",
    "assembled",
    "considering",
    "beholding",
    "observing",
    "amazed",
    "astonished",
    "astounded",
    "frightened",
    "terrified",
    "alarmed",
    "troubled",
    "distressed",
    "surprised",
    "pleased",
    "satisfied",
    "coming",
    "going",
    "standing",
    "sitting",
    "lying",
    "kneeling",
    "bowing",
    "entering",
    "leaving",
    "departing",
    "returning",
    "arriving",
    "approaching",
    "looking",
    "watching",
    "listening",
    "knowing",
    "praying",
    "fasting",
    "weeping",
    "crying",
    "rejoicing",
    "fearing",
    "being",
    "having",
    "doing",
    "making",
    "taking",
    "giving",
    "one",
    "ones",
    "other",
    "others",
    "another",
    "there",
    "here",
    "first",
    "second",
    "third",
    "himself",
    "herself",
    "themselves",
    "myself",
    "yourself",
    "itself",
    "ourselves",
    "yourselves",
    "selah",
    "amen",
    "passover",
    "sabbath",
    "pentecost",
    "feast",
    "jordan",
    "jerusalem",
    "egypt",
    "babylon",
    "jericho",
    "ecbatana",
    "tahpanhes",
    "chebar",
    "gilgal",
    "clauda",
    "magdalene",
    "scripture",
    "scriptures",
    "council",
    "quarter",
    "are",
    "is",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "let",
    "do",
    "ought",
    "must",
    "should",
    "once",
    "otherwise",
    "return",
    "preserve",
    "levitical",
    "kenizzite",
    "buzite",
    # Generic geographic/structural terms that never speak.
    "river",
    "sea",
    "ocean",
    "lake",
    "mountain",
    "mount",
    "hill",
    "valley",
    "plain",
    "plains",
    "wilderness",
    "desert",
    "city",
    "town",
    "village",
    "land",
    "country",
    "region",
    "coast",
    "gate",
    "well",
    "spring",
    "brook",
    "stream",
    "pool",
    "garden",
    "field",
    "vineyard",
    "house",
    "tent",
    "tabernacle",
    "temple",
    "altar",
    "ark",
    "throne",
    "road",
    "way",
    "highway",
    "path",
    "all",
    "every",
    "many",
    "some",
    "few",
    "each",
    "most",
    "woe",
    "amen",
    "verily",
    "truly",
    "surely",
    "who",
    "what",
    "where",
    "why",
    "how",
    "whose",
    "which",
    "whom",
    "this",
    "that",
    "these",
    "those",
    "such",
    "the",
    "rather",
    "again",
    "still",
    "just",
    "only",
    "even",
    "lo",
    "hear",
    "yea",
    "nay",
    "whenever",
    "whoever",
    "whatever",
    "you",
    "we",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "my",
    "mine",
    "him",
    "us",
    "them",
    "he",
    "she",
    "they",
    "it",
    "no",
    "not",
    "never",
}

# Capitalize each entry for the lookahead — the proper-noun pattern only
# considers capitalized words, so the lookahead only needs the Title-case forms.
_STOP_LOOKAHEAD = (
    r"(?!(?:"
    + "|".join(sorted({w.capitalize() for w in _STOP_WORDS}, key=len, reverse=True))
    + r")\b)"
)

# Generic capitalized proper-noun pattern. Guarded by `_STOP_LOOKAHEAD` so
# that finditer skips sentence-starters and pronoun forms before they swallow
# the position; `{2,}` excludes the bare pronoun "He". The trailing
# `(?:-[A-Z]?[a-z]+)*` allows hyphenated names like `Ben-hadad` and
# `Maher-shalal-hash-baz`.
_PROPER = rf"{_STOP_LOOKAHEAD}[A-Z][a-z]{{2,}}(?:-[A-Z]?[a-z]+)*"

# Possessive phrase like `Isaac's servants` or `Pharaoh's daughter`. Tried
# BEFORE `_PROPER` so the whole phrase is captured as the subject instead of
# just the leading proper name. Accepts both ASCII and curly apostrophe.
_POSSESSIVE = (
    rf"{_STOP_LOOKAHEAD}[A-Z][a-z]{{2,}}(?:-[A-Z]?[a-z]+)*" r"['’]s\s+[a-z]+(?:s|es)?"
)

_SUBJ = rf"(?:[Tt]he\s+)?(?:{_SPECIAL}|{_ROLES}|{_POSSESSIVE}|{_PROPER}|[Hh]e|[Ss]he|[Tt]hey|I)"

# Strict: subject directly followed by an attribution verb.
_ATTRIB = re.compile(
    rf"\b(?P<subj>{_SUBJ})\b\s+(?:also\s+|then\s+|again\s+)?" rf"(?P<verb>{_VERBS})\b"
)

# Loose: subject ... `, saying,` somewhere later in the same sentence.
# Used to catch patterns like `God blessed them, saying,` where the
# attribution verb is `saying` but it's not adjacent to the subject. No
# trailing `\s*` — that would greedily eat masked-quote spaces and push
# the match end past the opening quote in the original text.
_SAYING_LOOSE = re.compile(
    rf"\b(?P<subj>{_SUBJ})\b[^.!?“”]*?,\s*saying,?",
)

# Looser still: subject ... verb, allowing intervening words but not
# sentence boundaries. Catches `the sons of Joseph said,` (head noun far
# from the verb) and `Elihu the son of Barachel the Buzite spoke,`. Used
# only as a fallback after _ATTRIB and _SAYING_LOOSE.
_ATTRIB_LOOSE = re.compile(rf"\b(?P<subj>{_SUBJ})\b[^.!?“”]*?\b(?P<verb>{_VERBS})\b")

# Compound subject: `Laban and Bethuel replied,` — two subjects share one verb.
_ATTRIB_COMPOUND = re.compile(
    rf"\b(?P<subj1>{_SUBJ})\b\s+and\s+(?P<subj2>{_SUBJ})\b\s+"
    rf"(?:also\s+|then\s+|again\s+)?(?P<verb>{_VERBS})\b"
)

# Inverted attribution: `Thus says the LORD,` (prophetic formula — verb
# before subject). Matches `<verb> <subject>` so we can attribute these.
_INVERTED_ATTRIB = re.compile(
    rf"\b(?P<verb>says|said|saith|spoke|declares|declared|proclaims|proclaimed)"
    rf"\s+(?P<subj>{_SUBJ})\b"
)

# Divine revelation formula: `the word/vision/voice/etc. of <X> came …, saying,`.
# Here `<X>` is the actual speaker even though `of <X>` would normally be
# filtered as a genitive (non-subject) position. Common in prophets.
_DIVINE_REVELATION = re.compile(
    rf"\b[Tt]he\s+(?:word|vision|voice|prophecy|message|oracle|burden|"
    rf"commandment|decree|hand)\s+of\s+"
    rf"(?P<subj>(?:[Tt]he\s+)?(?:{_SPECIAL}|{_PROPER}))\b"
)

# A "named subject" — used for antecedent resolution. Excludes pronouns.
_NAMED_ONLY = re.compile(
    rf"\b(?:[Tt]he\s+)?(?:{_SPECIAL}|{_ROLES}|{_POSSESSIVE}|{_PROPER})\b"
)

_ALIASES = {
    "Lord Jesus": "Jesus",
    "Jesus Christ": "Jesus",
    "Christ Jesus": "Jesus",
    "Holy Spirit": "Holy Spirit",
    "Spirit": "Holy Spirit",
    "Christ": "Jesus",
    "LORD": "God",
    "LORD God": "God",
    "LORD of hosts": "God",
    "Lord God": "God",
    "Lord GOD": "God",
    "Abram": "Abraham",
    "Sarai": "Sarah",
    "serpent": "Satan",
    # Relational role-nouns are too generic without context; route them to
    # "unknown" so the manual overrides file can correct them per-verse.
    "mother": "unknown",
    "father": "unknown",
    "brother": "unknown",
    "sister": "unknown",
    "brothers": "unknown",
    "sisters": "unknown",
    "son": "unknown",
    "sons": "unknown",
    "daughter": "unknown",
    "daughters": "unknown",
    "people": "unknown",
}

_PRONOUNS = {"he", "she", "they", "i"}

# Addressee prepositions — when a named subject follows one of these, it's
# probably the listener, not the speaker.
_ADDRESSEE_PREP = re.compile(
    r"\b(?:[Tt]o|[Uu]nto|[Tt]oward|[Tt]owards|[Oo]f"
    r"|[Ii]n|[Aa]t|[Ff]rom|[Nn]ear)\s+$"
)

_SAYING_AT_END = re.compile(r",\s*saying,?\s*$")

# Like _SAYING_AT_END but for verses that end with `… and said,` /
# `… spoke,` etc. — the speech opens in the next verse and the speaker is
# the actor of this verse's verb.
_SPEECH_VERB_AT_END = re.compile(rf"\b(?:{_VERBS})\s*,?\s*$")

# NASB sometimes splits a speech intro across verses: verse N introduces
# the speaker but verse N+1 starts with `saying:` / `and said,` / etc.
# followed by the opening quote. Detect these kickoffs so the speaker is
# pulled from `pending_speaker` (set by the prior verse) or `narrative_subject`.
_SPEECH_VERB_INTRO = re.compile(
    rf"^\s*(?:[Aa]nd|[Tt]hen|[Bb]ut|[Ss]o|[Nn]ow)?\s*"
    rf"(?:{_VERBS})\s*[,:]?\s*{OPEN_Q}"
)

# Passive/anonymous quote introductions. When the verse hands off to a
# quote via "it is said,", "as it is written,", etc., no real speaker is
# named — the verse should resolve to null rather than to whatever pronoun
# antecedent happens to be earlier in the verse.
_PASSIVE_INTRO = re.compile(
    r"\b(?:"
    r"it\s+(?:is|was|shall\s+be)\s+(?:said|written|spoken|declared)|"
    r"as\s+it\s+(?:is|was)\s+(?:said|written)"
    r")\b",
    re.IGNORECASE,
)


_POSSESSIVE_NORM = re.compile(r"^([A-Z][a-z\-]+)(['’]s\s+\S+)$")


def _normalize(raw):
    """Apply naming rules: strip leading 'the', collapse aliases."""
    s = raw.strip()
    if s.lower().startswith("the "):
        s = s[4:].strip()
    s = re.sub(r"\s+", " ", s)
    # For possessive forms like `Abram's wife`, alias the leading name so
    # `Sarai's maid` → `Sarah's maid`, `Abram's servants` → `Abraham's servants`.
    m = _POSSESSIVE_NORM.match(s)
    if m:
        name, tail = m.group(1), m.group(2)
        if name in _ALIASES:
            return f"{_ALIASES[name]}{tail}"
    return _ALIASES.get(s, s)


def _is_pronoun(raw):
    return raw.strip().lower() in _PRONOUNS


def _is_stop_word(raw):
    s = raw.strip().lower()
    if s.startswith("the "):
        s = s[4:].strip()
    # Pronouns are in _STOP_WORDS only so the regex lookahead skips them at
    # the `_PROPER` level (leaving the explicit pronoun alternatives in _SUBJ
    # to fire). At the code level, pronoun matches must flow through to
    # pronoun resolution, so don't treat them as stop words here.
    if s in _PRONOUNS:
        return False
    return s in _STOP_WORDS


def _strip_nested(text):
    """Replace 'inner' speech with a placeholder so the inner speaker can't leak."""
    return re.sub(
        rf"{OPEN_SQ}[^{OPEN_SQ}{CLOSE_SQ}]*{CLOSE_SQ}",
        NESTED,
        text,
    )


def _narration_only(text, starts_in_quote):
    """Blank out content inside double-quote spans, preserving offsets."""
    out = list(text)
    in_quote = starts_in_quote
    for i, ch in enumerate(text):
        if ch == OPEN_Q:
            in_quote = True
            out[i] = " "
        elif ch == CLOSE_Q:
            in_quote = False
            out[i] = " "
        elif in_quote:
            out[i] = " "
    return "".join(out)


def _is_addressee(narration, match_start):
    """True if the named subject at `match_start` is preceded by 'to '/'unto '."""
    preceding = narration[max(0, match_start - 10) : match_start]
    return bool(_ADDRESSEE_PREP.search(preceding))


def _eligible_named_subjects(narration):
    """Yield (start, text) for named subjects not in addressee position.

    Skips pronouns picked up by the generic capitalized-word pattern and
    common sentence-starters. Possessive phrases are kept — the caller
    decides whether to use them as-is or extract the owner.
    """
    for m in _NAMED_ONLY.finditer(narration):
        raw = m.group(0)
        if _is_pronoun(raw) or _is_stop_word(raw):
            continue
        if _is_addressee(narration, m.start()):
            continue
        yield m.start(), raw


def _first_eligible_before(narration, before_pos):
    """Return the FIRST eligible named subject in `narration` before `before_pos`."""
    for start, text in _eligible_named_subjects(narration):
        if start >= before_pos:
            break
        return text
    return None


def _last_eligible(narration, before_pos=None):
    """Return the LATEST eligible named subject in `narration` before `before_pos`."""
    last = None
    for start, text in _eligible_named_subjects(narration):
        if before_pos is not None and start >= before_pos:
            break
        last = text
    return last


def _first_eligible(narration):
    for _, text in _eligible_named_subjects(narration):
        return text
    return None


def _is_proper_name(raw):
    """True if the matched subject is a proper name (not a generic role).

    Possessive phrases like `Balak's words` or `Isaac's servants` are NOT
    treated as proper names for narrative_subject tracking — their head
    noun is usually inanimate ("words", "hand", "tent") and tracking them
    causes pronoun fallback in the next verse to attribute to the wrong
    entity. (Possessives are still matched as the attribution subject when
    they're the explicit speaker — this filter only affects the
    `narrative_subject` carry-forward heuristic.)
    """
    s = raw.strip()
    if s.lower().startswith("the "):
        s = s[4:].strip()
    if not s or not s[0].isupper():
        return False
    if re.search(r"['’]s\b", s):
        return False
    return True


def _last_proper_eligible(narration):
    """Return the LAST eligible proper-named subject in `narration`.

    Used to track the protagonist of the current narrative scene. Only
    proper names that appear near the START of a clause count — clauses
    are split on `.`/`;`/`!`/`?`. This catches `Moses said,` and
    `Then Jesus came,` but rejects mid-clause appositives like
    `..., Tender and the only son...` (NASB's poetic capitalization in
    Proverbs/Psalms) which aren't real subjects of action.
    """
    last = None
    for clause in re.split(r"[.;!?]\s+", narration):
        for ns_start, ns_text in _eligible_named_subjects(clause):
            if ns_start > 30:
                break
            if _is_proper_name(ns_text):
                last = ns_text
                break
    return last


_INVERTED_CONTEXT = re.compile(
    r"(?:[.;,]\s+|" r"\b(?:Thus|Therefore|However|So|And|But|Now|Yet|For)\s+)$"
)


def _inverted_attrib_in_context(narration, verb_start):
    """True if a `<verb> <subject>` match is in a valid inverted-attribution
    context: at the start of narration, after a sentence boundary, after a
    recognized connective like `Thus`/`And`/`So`, or immediately after a
    blanked-out quote (whitespace-only preceding chars in narration form,
    which indicates a postfix `, declares the LORD` after a closed quote).
    Filters false positives like `Jacob's sons answered Shechem` where the
    verb-object phrase isn't actually a verb-first attribution.
    """
    if verb_start == 0:
        return True
    preceding = narration[max(0, verb_start - 25) : verb_start]
    if preceding.strip() == "":
        return True
    return bool(_INVERTED_CONTEXT.search(preceding))


def _quote_in_same_sentence(text, verb_end):
    """True if `text` has an open-quote after `verb_end` with no sentence
    boundary (`.`/`!`/`?`) between. Used to decide whether an attribution
    actually introduces the verse's quoted speech — `Moses said. Then Aaron
    said, "…"` should attribute to Aaron, not Moses.
    """
    rest = text[verb_end:]
    q_pos = rest.find(OPEN_Q)
    if q_pos < 0:
        return False
    return not any(c in ".!?" for c in rest[:q_pos])


class SpeakerExtractor:
    """Stateful walker. Call `extract(verses)` to yield (id, speakers) tuples.

    `overrides` is an optional `{verse_id: [speakers]}` dict. When a verse
    id is present, the override replaces the extracted result AND the
    internal state is re-seeded from the override so that continuation
    verses inherit the corrected speaker.
    """

    def __init__(self, overrides=None):
        self.active_speakers = []
        self.pending_speaker = None
        self.last_named = None  # latest eligible named subject across recent verses
        self.narrative_subject = (
            None  # first eligible named subject of the current scene
        )
        self.current_book = None
        self.overrides = overrides or {}

    def extract(self, verses):
        for v in verses:
            vid = v["id"]
            book = vid.split(":", 2)[1]
            if book != self.current_book:
                self.active_speakers = []
                self.pending_speaker = None
                self.last_named = None
                self.narrative_subject = None
                self.current_book = book
            raw = v["_text_"]
            speakers = self._process(raw)
            if vid in self.overrides:
                speakers = self.overrides[vid]
                self._reseed_state(raw, speakers)
            yield vid, speakers

    def _reseed_state(self, raw, speakers):
        """Re-set forward state to reflect an override's speakers.

        Called after `_process` has set state based on the original
        computation. Overrides need to propagate forward — continuation
        verses should inherit the override's speakers, not whatever the
        algorithm guessed.
        """
        text = raw.replace("*", "")
        text = _strip_nested(text)
        has_open = OPEN_Q in text
        has_close = CLOSE_Q in text
        if has_open or has_close:
            ends_in_quote = text.rfind(OPEN_Q) > text.rfind(CLOSE_Q)
        else:
            ends_in_quote = False

        # active_speakers: if this verse ends mid-quote, the override carries
        # forward to the next verse. Otherwise clear.
        if has_open or has_close:
            if ends_in_quote and speakers and speakers != ["unknown"]:
                self.active_speakers = list(speakers)
            else:
                self.active_speakers = []
        # If no markers, leave active_speakers as _process set it.

        # Use the first non-unknown speaker as the protagonist anchor.
        primary = next((s for s in speakers if s != "unknown"), None)
        if primary:
            self.narrative_subject = primary
            self.last_named = primary

        # pending_speaker only for saying-armed narration verses with no opener.
        if not has_open and _SAYING_AT_END.search(text):
            self.pending_speaker = primary
        else:
            self.pending_speaker = None

    def _process(self, raw):
        """Return a list of speakers for the verse.

        Empty list = pure narration. `["unknown"]` = speech present but
        unresolved. `["X"]` = single speaker. `["X", "Y"]` = compound
        subject sharing one utterance (e.g., `Laban and Bethuel replied,`).
        """
        text = raw.replace("*", "")
        text = _strip_nested(text)

        has_open = OPEN_Q in text
        has_close = CLOSE_Q in text
        if has_open or has_close:
            ends_in_quote = text.rfind(OPEN_Q) > text.rfind(CLOSE_Q)
        else:
            ends_in_quote = False

        starts_in_quote = bool(self.active_speakers)
        narration = _narration_only(text, starts_in_quote)

        # Passive/anonymous quote intro (`it is said,`, `as it is written,`)
        # — the quote has no real speaker; resolve to [] and skip the
        # attribution machinery entirely.
        is_passive = False
        for m in _PASSIVE_INTRO.finditer(narration):
            if OPEN_Q in text[m.end() : m.end() + 10]:
                is_passive = True
                break
        if is_passive:
            self.active_speakers = []
            self.pending_speaker = None
            return []

        # Multi-attribution detector: if the verse contains 2+ attribution
        # matches each opening their own quote (and both quotes complete
        # in-verse), this is a dialogue exchange. Collect all participants
        # rather than picking the first. Pronouns are resolved conservatively
        # — only via in-verse antecedent; otherwise `unknown` — so we don't
        # invent an answer from `narrative_subject` for a mixed exchange
        # like `She said to the servant, ... And the servant said, ...`
        # where we know one speaker and can't infer the other. Forward state
        # is cleared so subsequent continuation verses don't inherit a
        # confused narrative_subject.
        if (
            has_open
            and has_close
            and text.count(OPEN_Q) >= 2
            and text.count(CLOSE_Q) >= 2
        ):
            matches = []
            for m in _ATTRIB.finditer(narration):
                subj = m.group("subj")
                if _is_stop_word(subj) or _is_addressee(narration, m.start()):
                    continue
                if not _quote_in_same_sentence(text, m.end("verb")):
                    continue
                matches.append((subj, m.start()))
            if len(matches) >= 2:
                # If every match shares the same subject word (e.g.,
                # `she called ... she said`), this is one speaker uttering
                # two things — not a dialogue exchange. Treat as single.
                same_subj = len({s.strip().lower() for s, _ in matches}) == 1
                if not same_subj:
                    speakers = []
                    for subj, start in matches:
                        if _is_pronoun(subj):
                            speakers.append(
                                self._resolve_dialogue_pronoun(
                                    narration, start, speakers
                                )
                            )
                        else:
                            speakers.append(_normalize(subj))
                    # Dedupe preserving order.
                    seen = set()
                    deduped = []
                    for s in speakers:
                        if s not in seen:
                            seen.add(s)
                            deduped.append(s)
                    self.active_speakers = []
                    self.pending_speaker = None
                    self.narrative_subject = None
                    self.last_named = None
                    return deduped

        # Compound subject attribution: `Laban and Bethuel replied,` —
        # two conjoined subjects share one verb. Returns both speakers.
        compound_speakers = None
        for m in _ATTRIB_COMPOUND.finditer(narration):
            s1 = m.group("subj1")
            s2 = m.group("subj2")
            if _is_stop_word(s1) or _is_addressee(narration, m.start("subj1")):
                continue
            if _is_stop_word(s2) or _is_addressee(narration, m.start("subj2")):
                continue
            if _quote_in_same_sentence(text, m.end("verb")):
                sp1 = self._resolve(s1, narration, m.start("subj1"), saying_armed=False)
                sp2 = self._resolve(s2, narration, m.start("subj2"), saying_armed=False)
                compound_speakers = [sp1, sp2]
                break

        # Single-speaker attribution: strict, then `, saying,`-loose, then
        # subject-far-from-verb-loose. Only run if compound didn't match.
        in_verse_speaker = None
        if compound_speakers is None:
            # Divine revelation formula: `the word of the LORD came …, saying,`
            # — `the LORD` is the speaker despite the `of` genitive position.
            for m in _DIVINE_REVELATION.finditer(narration):
                subj = m.group("subj")
                if _is_stop_word(subj):
                    continue
                if (
                    _SAYING_AT_END.search(text)
                    or _SPEECH_VERB_AT_END.search(text)
                    or OPEN_Q in text[m.end() : m.end() + 200]
                ):
                    in_verse_speaker = self._resolve(
                        subj, narration, m.start("subj"), saying_armed=False
                    )
                    break

        if compound_speakers is None and in_verse_speaker is None:
            for m in _ATTRIB.finditer(narration):
                subj = m.group("subj")
                if _is_stop_word(subj) or _is_addressee(narration, m.start()):
                    continue
                if _quote_in_same_sentence(text, m.end("verb")):
                    resolved = self._resolve(
                        subj, narration, m.start(), saying_armed=False
                    )
                    # Skip alias-to-unknown matches (e.g., `father` matched
                    # closer to the verb than the actual proper name `Isaac`
                    # in `Isaac his father answered`) so a looser pattern can
                    # catch the real subject.
                    if resolved == "unknown":
                        continue
                    in_verse_speaker = resolved
                    break

            if in_verse_speaker is None:
                for m in _SAYING_LOOSE.finditer(narration):
                    subj = m.group("subj")
                    if _is_stop_word(subj) or _is_addressee(narration, m.start()):
                        continue
                    saying_end = m.end()
                    if OPEN_Q in text[saying_end : saying_end + 5]:
                        resolved = self._resolve(
                            subj, narration, m.start(), saying_armed=True
                        )
                        if resolved == "unknown":
                            continue
                        in_verse_speaker = resolved
                        break

            if in_verse_speaker is None:
                for m in _ATTRIB_LOOSE.finditer(narration):
                    subj = m.group("subj")
                    if _is_stop_word(subj) or _is_addressee(narration, m.start()):
                        continue
                    if _quote_in_same_sentence(text, m.end("verb")):
                        resolved = self._resolve(
                            subj, narration, m.start(), saying_armed=False
                        )
                        if resolved == "unknown":
                            continue
                        in_verse_speaker = resolved
                        break

            # Inverted attribution (`Thus says the LORD, "..."` — prophetic).
            if in_verse_speaker is None:
                for m in _INVERTED_ATTRIB.finditer(narration):
                    if not _inverted_attrib_in_context(narration, m.start("verb")):
                        continue
                    subj = m.group("subj")
                    if _is_stop_word(subj) or _is_addressee(narration, m.start("subj")):
                        continue
                    subj_end = m.end("subj")
                    if OPEN_Q in text[subj_end : subj_end + 60]:
                        in_verse_speaker = self._resolve(
                            subj, narration, m.start("subj"), saying_armed=False
                        )
                        break

        starts_with_open = text.lstrip().startswith(OPEN_Q)
        saying_kickoff = bool(_SPEECH_VERB_INTRO.match(text))

        if compound_speakers is not None:
            speakers = compound_speakers
        elif in_verse_speaker is not None:
            speakers = [in_verse_speaker]
        elif (starts_with_open or saying_kickoff) and self.pending_speaker is not None:
            # `saying: "..."` / `and said, "..."` continuation — prefer the
            # explicit pending speaker set by the prior verse's attribution.
            speakers = [self.pending_speaker]
        elif saying_kickoff and self.narrative_subject:
            # Fallback when prior verse didn't arm pending — use the
            # current narrative protagonist.
            speakers = [self.narrative_subject]
        elif self.active_speakers and (has_open or has_close):
            speakers = list(self.active_speakers)
        elif self.active_speakers and not (has_open or has_close):
            # Continuation across a verse with no quote markers (e.g., exo:20:6).
            speakers = list(self.active_speakers)
        elif has_open or has_close:
            speakers = ["unknown"]
        else:
            speakers = []

        # Update active_speakers for the next verse. The FULL list carries
        # forward so compound utterances ("Rachel and Leah said,") keep both
        # names attributed in continuation verses.
        if has_open or has_close:
            if ends_in_quote and speakers and speakers != ["unknown"]:
                self.active_speakers = list(speakers)
            else:
                self.active_speakers = []
        # If no markers: KEEP active_speakers (continuation across no-marker verse).

        # Update pending_speaker for verses that introduce speech but the
        # quote opens in the *next* verse. Trigger patterns:
        #   * `…, saying,` at end → use the saying-loose resolution
        #   * `… and said,` / `… spoke,` / `… answered,` at end → speaker
        #     is the first attribution subject in this verse
        #   * postfix `, declares the LORD.` / `, says the LORD.` — even
        #     when the verse closes its own quote, the next verse's new
        #     quote often belongs to the same declarer (NASB prophetic style)
        if not has_open and _SAYING_AT_END.search(text):
            self.pending_speaker = self._resolve_saying(narration)
        elif not has_open and _SPEECH_VERB_AT_END.search(text):
            self.pending_speaker = self._resolve_speech_at_end(narration)
        else:
            self.pending_speaker = None
        if self.pending_speaker is None:
            for m in _INVERTED_ATTRIB.finditer(narration):
                if not _inverted_attrib_in_context(narration, m.start("verb")):
                    continue
                subj = m.group("subj")
                if _is_stop_word(subj) or _is_addressee(narration, m.start("subj")):
                    continue
                self.pending_speaker = self._resolve(
                    subj, narration, m.start("subj"), saying_armed=False
                )
                break

        # Final fallback: if the verse has no quote opener but contains a
        # clear attribution match (subject + speech verb) that didn't open a
        # quote in-verse, treat it as a speech intro for the next verse —
        # `the angel of the LORD called to Abraham … from heaven,` followed
        # by `and said, "…"` in the next verse.
        if self.pending_speaker is None and not has_open:
            found = False
            for regex in (_ATTRIB, _ATTRIB_LOOSE):
                if found:
                    break
                for m in regex.finditer(narration):
                    subj = m.group("subj")
                    if _is_stop_word(subj) or _is_addressee(narration, m.start()):
                        continue
                    self.pending_speaker = self._resolve(
                        subj, narration, m.start(), saying_armed=False
                    )
                    found = True
                    break

        # Update last_named and narrative_subject from narration.
        last = _last_eligible(narration)
        if last:
            self.last_named = _normalize(last)
        last_proper = _last_proper_eligible(narration)
        if last_proper:
            self.narrative_subject = _normalize(last_proper)

        return speakers

    def _resolve(self, raw_subject, narration, attribution_start, saying_armed):
        if not _is_pronoun(raw_subject):
            return _normalize(raw_subject)
        # Pronoun. First, in-verse antecedent: prefer the FIRST eligible named
        # subject before this attribution (the main subject of the clause).
        antecedent = _first_eligible_before(narration, attribution_start)
        if antecedent:
            # If the antecedent is a possessive (`Jacob's anger`) and the
            # pronoun is singular, the implicit actor is the OWNER (Jacob).
            # Plural pronouns ("they") keep the full possessive — the head
            # noun is the group ("Isaac's servants" → "they" = the servants).
            if raw_subject.strip().lower() in {"he", "she"}:
                m = re.match(r"^([A-Z][a-z\-]+)['’]s\b", antecedent)
                if m:
                    return _normalize(m.group(1))
            return _normalize(antecedent)
        # Plural pronouns ("they") deliberately do NOT fall back to
        # `narrative_subject` or `last_named` — those are singular-biased
        # and yield nonsense like attributing `they said` to "Ophir" from a
        # genealogy verse chapters earlier. Without a clear in-verse
        # antecedent, the speaker group is unknown.
        if raw_subject.strip().lower() == "they":
            return "unknown"
        # Singular pronouns fall back to the main subject of the recent
        # narrative (typically the protagonist, e.g., Noah in Gen 9 or
        # Jesus in Mat 5). This beats `last_named`, which can be polluted
        # by trailing role-nouns like "son" or "father" used as objects.
        if self.narrative_subject:
            return self.narrative_subject
        if self.last_named:
            return self.last_named
        if self.active_speakers:
            return self.active_speakers[0]
        return "unknown"

    def _resolve_dialogue_pronoun(self, narration, pronoun_start, already_attributed):
        """Resolve a pronoun in a multi-attribution dialogue verse.

        Prefers any named subject in the verse that isn't already a speaker
        in this exchange. Falls back to addressee-position names (`said to
        Cain,` → Cain is the dialogue partner who replies next).
        """
        existing = {s for s in already_attributed if s != "unknown"}
        chosen = None
        # Pass 1: latest eligible (non-addressee) named subject before the
        # pronoun that isn't already attributed.
        for ns_start, ns_text in _eligible_named_subjects(narration):
            if ns_start >= pronoun_start:
                break
            cand = _normalize(ns_text)
            if cand and cand not in existing:
                chosen = cand
        if chosen:
            return chosen
        # Pass 2: include addressee-position names. In a multi-attribution
        # exchange, the prior turn's addressee is usually the next speaker.
        for m in _NAMED_ONLY.finditer(narration):
            if m.start() >= pronoun_start:
                break
            raw = m.group(0)
            if _is_stop_word(raw) or _is_pronoun(raw):
                continue
            cand = _normalize(raw)
            if cand and cand not in existing:
                chosen = cand
        return chosen if chosen else "unknown"

    def _resolve_speech_at_end(self, narration):
        """For verses ending with `… said,`/`… spoke,` etc. with no quote.

        Returns the FIRST non-stop, non-addressee attribution subject in
        the verse — the main actor of the speech-introducing verb. Used to
        arm `pending_speaker` for the next verse's `"…"` quote opener.
        """
        for regex in (_ATTRIB, _ATTRIB_LOOSE):
            for m in regex.finditer(narration):
                subj = m.group("subj")
                if _is_stop_word(subj) or _is_addressee(narration, m.start()):
                    continue
                return self._resolve(subj, narration, m.start(), saying_armed=False)
        return self.narrative_subject

    def _resolve_saying(self, narration):
        # Try loose pattern first (subject ... ', saying,').
        last = None
        for m in _SAYING_LOOSE.finditer(narration):
            if _is_stop_word(m.group("subj")):
                continue
            if _is_addressee(narration, m.start()):
                continue
            last = m
        if last:
            return self._resolve(
                last.group("subj"), narration, last.start(), saying_armed=True
            )
        # No subject before saying — fall back to the running narrative subject.
        if self.narrative_subject:
            return self.narrative_subject
        if self.last_named:
            return self.last_named
        return None
