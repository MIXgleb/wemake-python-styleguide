import ast
from collections import defaultdict
from typing import TypeAlias, final

from wemake_python_styleguide import constants
from wemake_python_styleguide.compat.aliases import FunctionNodes
from wemake_python_styleguide.compat.nodes import TypeAlias as ast_TypeAlias
from wemake_python_styleguide.compat.types import AnyTry
from wemake_python_styleguide.logic.nodes import get_context
from wemake_python_styleguide.logic.tree import decorators
from wemake_python_styleguide.types import AnyFunctionDef
from wemake_python_styleguide.violations import complexity
from wemake_python_styleguide.visitors.base import BaseNodeVisitor
from wemake_python_styleguide.visitors.decorators import alias

# Type aliases:
_ModuleMembers: TypeAlias = AnyFunctionDef | ast.ClassDef
_WithTypeParams: TypeAlias = _ModuleMembers | ast_TypeAlias
_ReturnLikeStatement: TypeAlias = ast.Return | ast.Yield


@final
@alias(
    'visit_module_members',
    (
        'visit_ClassDef',
        'visit_AsyncFunctionDef',
        'visit_FunctionDef',
    ),
)
class ModuleMembersVisitor(BaseNodeVisitor):
    """Counts classes and functions in a module."""

    def __init__(self, *args, **kwargs) -> None:
        """Creates a counter for tracked metrics."""
        super().__init__(*args, **kwargs)
        self._public_items_count = 0

    def visit_module_members(self, node: _ModuleMembers) -> None:
        """Counts the number of _ModuleMembers in a single module."""
        self._check_decorators_count(node)
        self._check_members_count(node)
        self.generic_visit(node)

    def _check_members_count(self, node: _ModuleMembers) -> None:
        """This method increases the number of module members."""
        if not isinstance(get_context(node), ast.Module):
            return

        if isinstance(
            node,
            FunctionNodes,
        ) and decorators.has_overload_decorator(node):
            return  # We don't count `@overload` defs as real defs

        self._public_items_count += 1

    def _check_decorators_count(self, node: _ModuleMembers) -> None:
        number_of_decorators = len(node.decorator_list)
        if number_of_decorators > self.options.max_decorators:
            self.add_violation(
                complexity.TooManyDecoratorsViolation(
                    node,
                    text=str(number_of_decorators),
                    baseline=self.options.max_decorators,
                ),
            )

    def _post_visit(self) -> None:
        if self._public_items_count > self.options.max_module_members:
            self.add_violation(
                complexity.TooManyModuleMembersViolation(
                    text=str(self._public_items_count),
                    baseline=self.options.max_module_members,
                ),
            )


@final
class ConditionsVisitor(BaseNodeVisitor):
    """Checks booleans for condition counts."""

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Counts the number of conditions."""
        self._check_conditions(node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Counts the number of compare parts."""
        self._check_compares(node)
        self.generic_visit(node)

    def _count_conditions(self, node: ast.BoolOp) -> int:
        counter = 0
        for condition in node.values:
            if isinstance(condition, ast.BoolOp):
                counter += self._count_conditions(condition)
            else:
                counter += 1
        return counter

    def _check_conditions(self, node: ast.BoolOp) -> None:
        conditions_count = self._count_conditions(node)
        if conditions_count > constants.MAX_CONDITIONS:
            self.add_violation(
                complexity.TooManyConditionsViolation(
                    node,
                    text=str(conditions_count),
                    baseline=constants.MAX_CONDITIONS,
                ),
            )

    def _check_compares(self, node: ast.Compare) -> None:
        is_all_equals = all(isinstance(op, ast.Eq) for op in node.ops)
        is_all_notequals = all(isinstance(op, ast.NotEq) for op in node.ops)
        can_be_longer = is_all_notequals or is_all_equals

        threshold = constants.MAX_COMPARES
        if can_be_longer:
            threshold += 1

        if len(node.ops) > threshold:
            self.add_violation(
                complexity.TooLongCompareViolation(
                    node,
                    text=str(len(node.ops)),
                    baseline=threshold,
                ),
            )


@final
class ElifVisitor(BaseNodeVisitor):
    """Checks the number of ``elif`` cases inside conditions."""

    def __init__(self, *args, **kwargs) -> None:
        """Creates internal ``elif`` counter."""
        super().__init__(*args, **kwargs)
        self._if_children: defaultdict[ast.If, list[ast.If]] = defaultdict(
            list,
        )

    def visit_If(self, node: ast.If) -> None:
        """Checks condition not to reimplement switch."""
        self._check_elifs(node)
        self.generic_visit(node)

    def _get_root_if_node(self, node: ast.If) -> ast.If:
        for root, children in self._if_children.items():
            if node in children:
                return root
        return node

    def _update_if_child(self, root: ast.If, node: ast.If) -> None:
        if node is not root:
            self._if_children[root].append(node)
        self._if_children[root].extend(node.orelse)  # type: ignore

    def _check_elifs(self, node: ast.If) -> None:
        has_elif = all(isinstance(if_node, ast.If) for if_node in node.orelse)

        if has_elif:
            root = self._get_root_if_node(node)
            self._update_if_child(root, node)

    def _post_visit(self) -> None:
        for root, children in self._if_children.items():
            real_children_length = len(set(children))
            if real_children_length > constants.MAX_ELIFS:
                self.add_violation(
                    complexity.TooManyElifsViolation(
                        root,
                        text=str(real_children_length),
                        baseline=constants.MAX_ELIFS,
                    ),
                )


@final
@alias(
    'visit_any_try',
    (
        'visit_Try',
        'visit_TryStar',
    ),
)
class TryExceptVisitor(BaseNodeVisitor):
    """Visits all try/except nodes to ensure that they are not too complex."""

    def visit_any_try(self, node: AnyTry) -> None:
        """Ensures that try/except is correct."""
        self._check_except_count(node)
        self._check_try_body_length(node)
        self._check_finally_body_length(node)
        self._check_exceptions_count(node)
        self.generic_visit(node)

    def _check_except_count(self, node: AnyTry) -> None:
        if len(node.handlers) > constants.MAX_EXCEPT_CASES:
            self.add_violation(
                complexity.TooManyExceptCasesViolation(
                    node,
                    text=str(len(node.handlers)),
                    baseline=constants.MAX_EXCEPT_CASES,
                ),
            )

    def _check_try_body_length(self, node: AnyTry) -> None:
        if len(node.body) > self.options.max_try_body_length:
            self.add_violation(
                complexity.TooLongTryBodyViolation(
                    node,
                    text=str(len(node.body)),
                    baseline=self.options.max_try_body_length,
                ),
            )

    def _check_finally_body_length(self, node: AnyTry) -> None:
        if len(node.finalbody) > self.options.max_lines_in_finally:
            self.add_violation(
                complexity.TooLongFinallyBodyViolation(
                    node,
                    text=str(len(node.finalbody)),
                    baseline=self.options.max_lines_in_finally,
                ),
            )

    def _check_exceptions_count(self, node: AnyTry) -> None:
        for except_handler in node.handlers:
            exc_type = except_handler.type
            if (
                isinstance(exc_type, ast.Tuple)
                and len(exc_type.elts) > self.options.max_except_exceptions
            ):
                self.add_violation(
                    complexity.TooManyExceptExceptionsViolation(
                        except_handler,
                        text=str(len(exc_type.elts)),
                        baseline=self.options.max_except_exceptions,
                    )
                )


@final
@alias(
    'visit_return_like',
    (
        'visit_Return',
        'visit_Yield',
    ),
)
class ReturnLikeStatementTupleVisitor(BaseNodeVisitor):
    """Finds too long ``tuples`` in ``yield`` and ``return`` expressions."""

    def visit_return_like(self, node: _ReturnLikeStatement) -> None:
        """Helper to get all ``yield`` and ``return`` nodes in a function."""
        self._check_return_like_values(node)
        self.generic_visit(node)

    def _check_return_like_values(self, node: _ReturnLikeStatement) -> None:
        if (
            isinstance(node.value, ast.Tuple)
            and len(node.value.elts) > constants.MAX_LEN_TUPLE_OUTPUT
        ):
            self.add_violation(
                complexity.TooLongOutputTupleViolation(
                    node,
                    text=str(len(node.value.elts)),
                    baseline=constants.MAX_LEN_TUPLE_OUTPUT,
                ),
            )


@final
class TupleUnpackVisitor(BaseNodeVisitor):
    """Finds statements with too many variables receiving an unpacked tuple."""

    def visit_Assign(self, node: ast.Assign) -> None:
        """Finds statements using too many variables to unpack a tuple."""
        self._check_tuple_unpack(node)
        self.generic_visit(node)

    def _check_tuple_unpack(self, node: ast.Assign) -> None:
        if not isinstance(node.targets[0], ast.Tuple):
            return

        if len(node.targets[0].elts) <= self.options.max_tuple_unpack_length:
            return

        self.add_violation(
            complexity.TooLongTupleUnpackViolation(
                node,
                text=str(len(node.targets[0].elts)),
                baseline=self.options.max_tuple_unpack_length,
            ),
        )


@final
@alias(
    'visit_typed_params',
    (
        'visit_ClassDef',
        'visit_AsyncFunctionDef',
        'visit_FunctionDef',
        'visit_TypeAlias',
    ),
)
class TypeParamsVisitor(BaseNodeVisitor):  # pragma: >=3.12 cover
    """Finds wrong type parameters."""

    def visit_typed_params(self, node: _WithTypeParams) -> None:
        """Finds all objects with ``type_params``."""
        self._check_type_params_count(node)
        self.generic_visit(node)

    def _check_type_params_count(
        self,
        node: _WithTypeParams,
    ) -> None:
        type_params = getattr(node, 'type_params', [])
        if len(type_params) > self.options.max_type_params:
            self.add_violation(
                complexity.TooManyTypeParamsViolation(
                    node,
                    text=str(len(type_params)),
                    baseline=self.options.max_type_params,
                )
            )
