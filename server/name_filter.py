"""Rudimentary check that keeps obscene player and lobby names out of the lobby list.

Words come from the better-profanity word list and match as whole words. A few strong words also
match inside other text ("xXfuckXx"). Common leetspeak and accents are normalised first.
"""
import re
import unicodedata
from functools import lru_cache
from importlib import resources

MAX_NAME_LENGTH = 24

# Harmless or common words that appear in the word list.
ALLOWED = frozenset('''
    god kill murder drunk fat ugly stupid gay gays queer lesbians strip pot weed virgin stroke slave
    oral lmao lmfao wtf omg screw screwed screwing hiv organ facial wang pee jerk thrust slope heroin
    woody vodka rum sniper moron dummy weirdo urine womb uterus willy paddy pawn opium knob fanny len
    maxi sob potty tramp seaman pollock hemp dong lust reich thug stoned vomit vulgar snatch crotch
    sissy weiner hell arian meth hump shi guido massa revue uzi wad steamy trashy sleazy snuff pms
    seduce enlargement
'''.split())

# Matched anywhere in the name, ignoring spaces and punctuation.
STRONG_WORDS = ('fuck', 'shit', 'cunt', 'bitch', 'nigg', 'faggot', 'whore', 'slut')
# Innocent words containing a strong word; removed before the substring check.
INNOCENT_WORDS = ('scunthorpe', 'niggle', 'niggardly', 'snigger', 'kinoshita', 'matsushita', 'yamashita')

_LEET = str.maketrans('013457@$!', 'oieastasi')


def _normalise(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(c for c in text if not unicodedata.combining(c)).translate(_LEET)


@lru_cache(maxsize=1)
def _blocked_words():
    raw = resources.files('better_profanity').joinpath('profanity_wordlist.txt').read_text(encoding='utf-8')
    words = {re.sub('[^a-z]', '', _normalise(line)) for line in raw.splitlines()}
    return frozenset(w for w in words if len(w) >= 3) - ALLOWED


def contains_blocked_word(text):
    text = _normalise(text)
    if any(word in _blocked_words() for word in re.findall('[a-z]+', text)):
        return True
    compact = re.sub('[^a-z]', '', text)
    for word in INNOCENT_WORDS:
        compact = compact.replace(word, ' ')
    return any(word in compact for word in STRONG_WORDS)


def clean_name(raw, label):
    """Returns (name, None) with whitespace tidied, or (None, error message) if the name is rejected."""
    name = ' '.join(raw.split()) if isinstance(raw, str) else ''
    if not name:
        return None, f'Enter a {label}.'
    if len(name) > MAX_NAME_LENGTH:
        return None, f'The {label} must be {MAX_NAME_LENGTH} characters or fewer.'
    if any(unicodedata.category(c).startswith('C') for c in name):
        return None, f'The {label} contains characters that are not allowed.'
    if contains_blocked_word(name):
        return None, f"That {label} isn't allowed. Please choose another."
    return name, None
