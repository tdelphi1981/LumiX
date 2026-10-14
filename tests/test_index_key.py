from dataclasses import dataclass

from lumix import LXIndexDimension, LXVariable


@dataclass(frozen=True)
class Plant:
    id: str


@dataclass(frozen=True)
class Customer:
    id: str


def test_index_key_uses_index_func():
    x = LXVariable[Plant, float]("x").indexed_by(lambda p: p.id).from_data([Plant("a")])
    assert x.index_key(Plant("a")) == "a"


def test_index_key_of_cartesian_family_is_tuple_of_dimension_keys():
    x = LXVariable[tuple, float]("x").indexed_by_product(
        LXIndexDimension(Plant, lambda p: p.id).from_data([Plant("a")]),
        LXIndexDimension(Customer, lambda c: c.id).from_data([Customer("r")]),
    )
    assert x.index_key((Plant("a"), Customer("r"))) == ("a", "r")


def test_index_key_without_key_function_is_the_instance():
    x = LXVariable[str, float]("x").from_data(["a"])
    assert x.index_key("a") == "a"
