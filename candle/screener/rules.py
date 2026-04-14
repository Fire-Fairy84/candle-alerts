"""Screener rule definitions.

A Rule is a named, composable unit that combines one or more condition primitives.
Multiple conditions within a rule are evaluated with AND logic (all must be True).
"""

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


ConditionFn = Callable[[pd.DataFrame], bool]


@dataclass
class Rule:
    """A named screener rule composed of one or more conditions.

    All conditions are evaluated with AND logic: the rule fires only when every
    condition returns True.

    Attributes:
        name: Human-readable rule name used in alert messages.
        conditions: List of callables that each accept a DataFrame and return bool.
    """

    name: str
    conditions: list[ConditionFn] = field(default_factory=list)

    def evaluate(self, df: pd.DataFrame) -> bool:
        """Return True if all conditions are met on the given DataFrame.

        Short-circuits on the first False condition. Returns True vacuously
        when the conditions list is empty.

        Args:
            df: DataFrame with OHLCV data and pre-computed indicator columns.

        Returns:
            True if every condition returns True, False if any returns False.
        """
        return all(condition(df) for condition in self.conditions)
