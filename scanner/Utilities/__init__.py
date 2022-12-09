"""
Some utilities which are very unspecific and could be used in literally any project.
"""
from typing import Iterable, Tuple, Dict


def merge_tuples(tuples: Iterable[Tuple], duplicates=False):
    """
    Merges multiple tuples into one tuple of tuples, where each inner tuple contains the elements
    of the original tuples at that index.
    :param tuples: iterable of tuples to be merged
    :param duplicates: whether to allow duplicates within the inner tuples or not, default is False
    :return: merged tuples
    """
    max_len = max([len(t) for t in tuples], default=0)
    merged = ()
    for i in range(max_len):
        components = ()
        for t in tuples:
            if i < len(t) and (duplicates or t[i] not in components):
                components += (t[i],)
        merged += (components,)
    return merged


def hashable(item) -> bool:
    """
    Check if an object is actually hashable (not just a subclass of collections.abc.Hashable).
    :param item: item to be checked
    :return: True iff hash(item) will succeed
    """
    try:
        hash(item)
        return True
    except TypeError:
        return False


def int_or_none(param):
    try:
        return int(param)
    except TypeError:
        return None


def stringify_dict(data: Dict):
    if not data:
        return "{}"
    items = []
    for k, v in data.items():
        items.append(f"{k}={v}")
    return "{" + "&".join(items) + "}"
