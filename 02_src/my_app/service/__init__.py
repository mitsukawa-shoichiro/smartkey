from importlib import import_module


__all__ = [
    "get_card",
    "get_state",
    "set_state",
]


def __getattr__(name):
    """
    必要になったときだけcard_sysを読み込む
    """

    if name in __all__:
        card_sys = import_module(
            ".card_sys",
            package=__name__,
        )
        value = getattr(card_sys, name)
        globals()[name] = value
        return value

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )