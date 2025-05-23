import pytest

from wemake_python_styleguide.violations.oop import (
    ShadowedClassAttributeViolation,
)
from wemake_python_styleguide.visitors.ast.classes.attributes import (
    ClassAttributeVisitor,
)

# Can raise:

class_attribute = """
class ClassWithAttrs:
    {0} = 0

    def __init__(self) -> None:
        self.{1} = 2
"""

class_annotated_attribute = """
class ClassWithAttrs:
    {0}: int = 0

    def __init__(self) -> None:
        self.{1} = 2
"""

class_attribute_logic = """
class ClassWithAttrs:
    if some_flag:
        {0} = 0

    def __init__(self) -> None:
        self.{1} = 2
"""

class_attribute_runtime = """
class ClassWithAttrs:
    {0} = 0

    def constructor(self) -> None:
        self.{1} = 2
"""

class_attribute_annotated = """
class ClassWithAttrs:
    {0}: int = 0

    def __init__(self) -> None:
        self.{1} = 2
"""

class_with_unrelated_decorator1 = """
@not_a_dataclass
class ClassWithAttrs:
    {0}: int = 0

    def __post_init__(self) -> None:
        self.{1} = 2
"""

class_with_unrelated_decorator2 = """
@not_dataclasses[0]
class ClassWithAttrs:
    {0}: int = 0

    def __post_init__(self) -> None:
        self.{1} = 2
"""

# Safe:

class_annotation = """
class ClassWithAttrs:
    {0}: int

    def __init__(self) -> None:
        self.{1} = 2
"""

class_attribute_usage = """
class ClassWithAttrs:
    {0} = 0

    def print_field(self) -> None:
        print(self.{1})
"""

class_attribute_regular_assign = """
class ClassWithAttrs:
    def constructor(self) -> None:
        {0} = 0
        self.{1} = 2
"""

class_attribute_with_other = """
class ClassWithAttrs:
    {0} = 0

    def constructor(self) -> None:
        other.{0} = 0
        self.{1} = 2
"""

class_complex_attribute = """
class ClassWithAttrs:
    prefix.{0} = 0

    def __init__(self) -> None:
        self.{1} = 2
"""

class_complex_attribute_annotated = """
class ClassWithAttrs:
    prefix.{0}: int = 0

    def __init__(self) -> None:
        self.{1} = 2
"""

class_with_dataclass_decorator1 = """
@dataclass
class ClassWithAttrs:
    {0}: int = 0

    def __post_init__(self) -> None:
        self.{1} = 2
"""

class_with_dataclass_decorator2 = """
@dataclass(slots=True)
class ClassWithAttrs:
    {0}: int = 0

    def __post_init__(self) -> None:
        self.{1} = 2
"""

regular_assigns = """
{0} = 0
{1} = 2
"""


@pytest.mark.parametrize(
    'code',
    [
        class_attribute,
        class_annotated_attribute,
        class_attribute_runtime,
        class_attribute_annotated,
        class_attribute_logic,
        class_with_unrelated_decorator1,
        class_with_unrelated_decorator2,
    ],
)
@pytest.mark.parametrize(
    'field_name',
    [
        'field1',
        '_field1',
        '__field1',
    ],
)
def test_incorrect_fields(
    assert_errors,
    assert_error_text,
    parse_ast_tree,
    default_options,
    code,
    field_name,
):
    """Testing that incorrect fields are prohibited."""
    tree = parse_ast_tree(code.format(field_name, field_name))

    visitor = ClassAttributeVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [ShadowedClassAttributeViolation])
    assert_error_text(visitor, field_name)


@pytest.mark.parametrize(
    'code',
    [
        class_attribute,
        class_annotated_attribute,
        class_attribute_runtime,
        class_attribute_annotated,
        class_annotation,
        class_complex_attribute,
        class_complex_attribute_annotated,
        class_attribute_usage,
        class_attribute_logic,
        class_attribute_regular_assign,
        class_attribute_with_other,
        class_with_unrelated_decorator1,
        class_with_unrelated_decorator2,
        class_with_dataclass_decorator1,
        class_with_dataclass_decorator2,
        regular_assigns,
    ],
)
@pytest.mark.parametrize(
    ('field1', 'field2'),
    [
        ('field1', 'field2'),
        ('_field1', '_field2'),
        ('__field1', '__field2'),
    ],
)
def test_correct_fields(
    assert_errors,
    parse_ast_tree,
    default_options,
    code,
    field1,
    field2,
):
    """Testing that correct fields are allowed."""
    tree = parse_ast_tree(code.format(field1, field2))

    visitor = ClassAttributeVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])


@pytest.mark.parametrize(
    'code',
    [
        class_annotation,
        class_attribute_usage,
        class_attribute_regular_assign,
        regular_assigns,
        class_complex_attribute,
        class_complex_attribute_annotated,
        class_with_dataclass_decorator1,
        class_with_dataclass_decorator2,
    ],
)
@pytest.mark.parametrize(
    ('field1', 'field2'),
    [
        ('field1', 'field1'),
        ('_field1', '_field1'),
        ('__field1', '__field1'),
    ],
)
def test_safe_fields(
    assert_errors,
    parse_ast_tree,
    default_options,
    code,
    field1,
    field2,
):
    """Testing that safe fields can be used everywhere."""
    tree = parse_ast_tree(code.format(field1, field2))

    visitor = ClassAttributeVisitor(default_options, tree=tree)
    visitor.run()

    assert_errors(visitor, [])
