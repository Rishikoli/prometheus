"""A rule-based slice of the CPC: which subclasses count as fields.

The slice is defined by class *prefixes* in a JSON file that is written down before
any result is seen. It is never defined by which fields turned out to grow fast:
that would put the answer into the backtest.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

_PREFIX = re.compile(r"^[A-Z][A-Z0-9]{0,3}$")


class SliceError(ValueError):
    pass


@dataclass(frozen=True)
class SliceRule:
    name: str
    include: dict = field(default_factory=dict)  # domain label -> list of prefixes
    exclude: tuple = ()

    @property
    def include_prefixes(self) -> list[str]:
        return sorted({p for ps in self.include.values() for p in ps})

    def matches(self, code: str) -> bool:
        return code.startswith(tuple(self.include_prefixes)) and not code.startswith(self.exclude or ("\0",))

    def sql(self, col: str) -> str:
        """A SQL boolean expression over column `col`. Prefixes are validated, so this is safe."""
        inc = " OR ".join(f"{col} LIKE '{p}%'" for p in self.include_prefixes)
        exc = " OR ".join(f"{col} LIKE '{p}%'" for p in self.exclude)
        return f"(({inc})" + (f" AND NOT ({exc})" if exc else "") + ")"

    def domain_of(self, code: str) -> str | None:
        for label, prefixes in self.include.items():
            if code.startswith(tuple(prefixes)):
                return label
        return None


def _check(prefixes, what):
    for p in prefixes:
        if not isinstance(p, str) or not _PREFIX.match(p):
            raise SliceError(f"{what}: {p!r} is not a CPC prefix (1 to 4 upper-case letters or digits)")


def from_dict(d: dict) -> SliceRule:
    include = d.get("include") or {}
    exclude = tuple(d.get("exclude") or ())
    if not include:
        raise SliceError("slice has no 'include' prefixes")
    for label, ps in include.items():
        _check(ps, f"include[{label}]")
    _check(exclude, "exclude")
    return SliceRule(name=d.get("name", "custom"), include={k: list(v) for k, v in include.items()}, exclude=exclude)


def load(path_or_name: str | Path | None) -> SliceRule | None:
    """`None` or 'all' -> no slice. A bare name such as 'deeptech' loads the bundled file."""
    if path_or_name in (None, "", "all"):
        return None
    p = Path(str(path_or_name))
    if p.exists():
        return from_dict(json.loads(p.read_text()))
    try:
        text = resources.files("prometheus.slices").joinpath(f"{path_or_name}.json").read_text()
    except (FileNotFoundError, ModuleNotFoundError):
        raise SliceError(f"slice '{path_or_name}' is neither a file nor a bundled slice") from None
    return from_dict(json.loads(text))
