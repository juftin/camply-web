# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Utility functions for providers.
"""

_EXCEPTIONS: frozenset[str] = frozenset({
    "of",
    "the",
    "and",
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "by",
})


def normalize_name(name: str | None) -> str | None:
    """
    Normalize a campground or recreation area name.

    If the string is entirely uppercase or entirely lowercase, convert to
    title case (respecting common exception words).  Otherwise return
    the name unchanged — it is already properly cased.

    Exception words (lowered except when they are the first word):
    of, the, and, in, on, at, to, for, with, by

    Parameters
    ----------
    name : str | None
        The name to normalize.

    Returns
    -------
    str | None
        The normalized name, or ``None`` / empty string as-is.
    """
    if not name:
        return name

    if not name.isupper() and not name.islower():
        return name

    words = name.lower().split(" ")
    result: list[str] = []
    for i, word in enumerate(words):
        if not word:
            result.append(word)
            continue
        if i == 0 or word not in _EXCEPTIONS:
            result.append(word[0].upper() + word[1:])
        else:
            result.append(word)
    return " ".join(result)
