from typing import NamedTuple


class version_info(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int

    @property
    def __version__(self) -> str:
        return (
            f"{self.major}.{self.minor}.{self.micro}"
            + (
                f"{'r' if self.releaselevel[0] == 'c' else ''}{self.releaselevel[0]}{self.serial}",
                "",
            )[self.releaselevel == "final"]
        )

    def __str__(self) -> str:
        return f"{__name__} {self.__version__} / {__version_time__}"

    def __repr__(self) -> str:
        return (
            f"{__name__}.{type(self).__name__}"
            f"({', '.join('{}={!r}'.format(*nv) for nv in zip(self._fields, self))})"
        )


__version_info__ = version_info(3, 2, 0, "beta", 2)
__version_time__ = "14 Sep 2024 21:44 UTC"
__version__ = __version_info__.__version__
__versionTime__ = __version_time__

__all__ = [
    "__version_info__",
    "__version_time__",
    "__version__",
    "__versionTime__",
]