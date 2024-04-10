from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .schemes import (
    ANDRequirement,
    EquivalenceRequirement,
    ImplicationRequirement,
    NegatedRequirement,
    ORRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)

T = TypeVar("T")


@dataclass(frozen=True)
class RequirementVisitor(Generic[T]):
    simple_visitor: Callable[[SimpleRequirement], T]
    negated_visitor: Callable[[T], T]
    and_visitor: Callable[[Iterable[T]], T]
    or_visitor: Callable[[Iterable[T]], T]
    xor_visitor: Callable[[Iterable[T]], T]
    implication_visitor: Callable[[T, T], T]
    equivalence_visitor: Callable[[Iterable[T]], T]


def visit_requirements(requirement: Requirement, visitor: RequirementVisitor[T]) -> T:
    if isinstance(requirement, SimpleRequirement):
        return visitor.simple_visitor(requirement)
    elif isinstance(requirement, NegatedRequirement):
        return visitor.negated_visitor(visit_requirements(requirement.negated, visitor))
    elif isinstance(requirement, ANDRequirement):
        return visitor.and_visitor(
            visit_requirements(subrequirement, visitor)
            for subrequirement in requirement.and_
        )
    elif isinstance(requirement, ORRequirement):
        return visitor.or_visitor(
            visit_requirements(subrequirement, visitor)
            for subrequirement in requirement.or_
        )
    elif isinstance(requirement, XORRequirement):
        return visitor.xor_visitor(
            visit_requirements(subrequirement, visitor)
            for subrequirement in requirement.xor
        )
    elif isinstance(requirement, ImplicationRequirement):
        return visitor.implication_visitor(
            visit_requirements(requirement.if_, visitor),
            visit_requirements(requirement.implies, visitor),
        )
    elif isinstance(requirement, EquivalenceRequirement):
        return visitor.equivalence_visitor(
            visit_requirements(subrequirement, visitor)
            for subrequirement in requirement.equivalent
        )
