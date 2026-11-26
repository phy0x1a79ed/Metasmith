from __future__ import annotations

import pytest

from metasmith.agents import TargetBuilder, TargetSpec


def test_add_returns_handle():
    tb = TargetBuilder()
    a = tb.Add("ns::t")
    assert isinstance(a, TargetSpec)
    assert a.dtype_name == "ns::t"
    assert a.parents == ()


def test_lineage_distinct_duplicates_are_allowed():
    tb = TargetBuilder()
    parent_a = tb.Add("ns::parent_a")
    parent_b = tb.Add("ns::parent_b")
    fork_a = tb.Add("ns::child", parents={parent_a})
    fork_b = tb.Add("ns::child", parents={parent_b})
    assert fork_a != fork_b
    specs = tb.resolve()
    assert specs == [parent_a, parent_b, fork_a, fork_b]
    assert len(tb) == 4


def test_structurally_identical_duplicate_is_rejected():
    tb = TargetBuilder()
    tb.Add("ns::t")
    with pytest.raises(AssertionError, match="identical parents"):
        tb.Add("ns::t")


def test_identical_duplicate_with_same_parents_is_rejected():
    tb = TargetBuilder()
    p = tb.Add("ns::parent")
    tb.Add("ns::t", parents={p})
    with pytest.raises(AssertionError, match="identical parents"):
        tb.Add("ns::t", parents={p})


def test_namespace_format_enforced():
    tb = TargetBuilder()
    with pytest.raises(AssertionError, match="namespace::type_name"):
        tb.Add("no_namespace_separator")


def test_resolve_preserves_insertion_order():
    tb = TargetBuilder()
    a = tb.Add("ns::a")
    b = tb.Add("ns::b", parents={a})
    c = tb.Add("ns::c", parents={a, b})
    specs = tb.resolve()
    assert specs.index(a) < specs.index(b) < specs.index(c)


def test_member_set_is_a_parent_and_takes_part_in_equality():
    tb = TargetBuilder()
    asm = tb.Add("ns::asm")
    a = tb.Add("ns::refined", parents=[asm, tb.Set("ns::b2", "ns::b1")])
    b = tb.Add("ns::refined", parents=[asm, tb.Set("ns::b1", "ns::b2", "ns::b3")])
    assert a.members == ("ns::b1", "ns::b2")
    assert a != b
    with pytest.raises(AssertionError, match="identical parents"):
        tb.Add("ns::refined", parents=[asm, tb.Set("ns::b1", "ns::b2")])


@pytest.mark.parametrize("names, match", [((), "at least one"), (("ns::b1", "ns::b1"), "twice")])
def test_member_set_refuses_empty_and_repeats(names, match):
    with pytest.raises(AssertionError, match=match):
        TargetBuilder().Set(*names)


def test_one_member_set_per_target():
    tb = TargetBuilder()
    with pytest.raises(AssertionError, match="more than one member set"):
        tb.Add("ns::refined", parents=[tb.Set("ns::b1"), tb.Set("ns::b2")])


def test_pack_round_trips_through_add_all():
    tb = TargetBuilder()
    asm = tb.Add("ns::asm")
    tb.Add("ns::refined", parents=[asm, tb.Set("ns::b1", "ns::b2")])
    tb.Add("ns::plain", parents=[asm])
    wire = tb.Pack()
    assert wire == ["ns::asm", {"type": "ns::refined", "parents": [0], "set": ["ns::b1", "ns::b2"]}, {"type": "ns::plain", "parents": [0]}]
    again = TargetBuilder()
    again.AddAll(wire)
    assert again.resolve() == tb.resolve()
