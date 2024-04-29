from asyncio import TaskGroup
from collections.abc import Awaitable, Iterable
from dataclasses import dataclass
from typing import Callable

from .schemes import (
    ANDRequirement,
    ImplicationRequirement,
    NegatedRequirement,
    ORRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)


@dataclass(frozen=True)
class RequirementVisitor[T]:
    simple_visitor: Callable[[SimpleRequirement], Awaitable[T]]
    negated_visitor: Callable[[T], Awaitable[T]]
    and_visitor: Callable[[Iterable[T]], Awaitable[T]]
    or_visitor: Callable[[Iterable[T]], Awaitable[T]]
    xor_visitor: Callable[[Iterable[T]], Awaitable[T]]
    implication_visitor: Callable[[T, T], Awaitable[T]]
    equivalence_visitor: Callable[[Iterable[T]], Awaitable[T]]


async def visit_requirements[
    T
](requirement: Requirement, visitor: RequirementVisitor[T]) -> T:
    if isinstance(requirement, SimpleRequirement):
        return await visitor.simple_visitor(requirement)
    elif isinstance(requirement, NegatedRequirement):
        return await visitor.negated_visitor(
            await visit_requirements(requirement.negated, visitor)
        )
    elif isinstance(requirement, ImplicationRequirement):
        async with TaskGroup() as group:
            if_task = group.create_task(visit_requirements(requirement.if_, visitor))
            implies_task = group.create_task(
                visit_requirements(requirement.implies, visitor)
            )

        return await visitor.implication_visitor(await if_task, await implies_task)
    else:
        if isinstance(requirement, ANDRequirement):
            children = requirement.and_
            visitor_operation = visitor.and_visitor
        elif isinstance(requirement, ORRequirement):
            children = requirement.or_
            visitor_operation = visitor.or_visitor
        elif isinstance(requirement, XORRequirement):
            children = requirement.xor
            visitor_operation = visitor.xor_visitor
        else:
            children = requirement.equivalent
            visitor_operation = visitor.equivalence_visitor

        async with TaskGroup() as group:
            argument_tasks = [
                group.create_task(visit_requirements(child, visitor))
                for child in children
            ]

        return await visitor_operation([await argument for argument in argument_tasks])
