"""
Commodity codes are 10-digit codes that refer to specific products. Traders must
put these codes on their declaration forms when importing or exporting goods.

Nomenclature, also known as goods classification, goods nomenclature or
commodity code classification, is the name for the full list of products in the
UK Tariff.

TP-803: Commodity Tree Changes
======================
ISSUES TO CONSIDER WHEN CHANGING THE TREE
Changes to the commodity tree have two main types of considerations:
1. Do we have a correct commodity tree after the change?
  - e.g. are all parent, child, sibling and other relations as they should be
  - the question applies for the changing commodity
    as well as all commodities in its hierarchy prior and post change
    (these may or may not be the same depending on the change)
2. Have we dealt with any side effects on any related taric records
  - related records may include measures, footnote associations, etc.
  - affected records may be related to the changing commodity itself
    or to any commodity in the surrounding hierarchy pre- and post-change
  - side effects are incidental violations of business rules
    resulting form the changes made to the commodity tree
    and as such can be caught in the vast majority of cases
    using existing business rule validation logic in TaMaTo

REQUIREMENTS FOR TACKLING THE ISSUES
B. In order to handle well commodity tree chanegs in the context of
the above two main considerations, we need to adopt a new approach that:
1. Avoids late fails in terms of firing off business rule violations
  or post-mortem re-evaluations of the materialized commodity hierarchy
  - this is particularly relevant when making large-scale
    changes to the tree, e.g. in the context of HS22
2. Takes advantage of early detection of side effects by providing
  automated decision logic for the correct remedy in each case

TP-803's BOOTSTRAPPING IMPLEMENTATION
The new approach in TP-803 satisfies the above criteria by
"bootstrapping" any pending changes to the commodity tree,
providing the ability to view "before" and "after" snapshots
of the commodity tree hierarchy pre- and post- pending changes,
detecting any potential side effects on related records,
and providing a list of pending related record changes
that need to be applied alongside the commodity changes.

The following constructs make the bootstrapping approach possible:
1. Commodity wrapper (inherits form a new TrackedModelWrapper dataclass)
  - the primary benefit of the wrapper is the ability to "fake"
    changes to the wrapped underlying record for the purposes of
    previewing the effects and side effects of the change.
  - one example is "masking" relations fields to avoid complications
    of dealing with related meta records (e.g. indents in commodities).
  - the wrapper provides a range of "convenience" methods as additional perks

2. CommodityCollection
  - this is just a bag of commodities
    -- included commodities may or may not be effective at the same point in time
    -- the may wrap any version of a good object
  - commodity changes are applied to this collection construct

3. CommodityTreeSnapshot
  - a collection provides the ability to take "snapshots"
  - a snapshot is a collection of commodities that are in effect
    as of a given moment, and constitute the tree hierarchy as of that moment
  - a snapshot can be taken based on one of two "clocks", but not both:
    -- a calendar clock (what goods where in effect as of date x)
    -- a transaction clock (what goods where in effect as of transaction x)
    -- see the Tariff Manual for further discussion on calendar vs transaction clocks
  - a snapshot has a tree hierarchy with parent, children and sibling relations
    as well as traversal-style relations such as ancestors and descendants

4. SnapshotDiff
  - a dedicated construct for evaluating snapshot diffs
  - the key benefit of the construct is clean code
  - a diff is evaluated in terms of members of a single relation for a single commodity
    -- e.g. what is the difference in the siblings of commodity x
       between snapshot a and snapshot b?
  - there are two motivations for using a snapshot diff:
    -- compare the "before" and "after" snapshots around a commodity change
    -- compare the state of the commodity tree at two different points in time
       (even outside the context of a commodity change)

5. CommodityChange
  - a dedicated construct for pending commodity changes
  - this construct serves as a "watchdog" for pending changes:
    -- it evaluates the "sanity" of a requested change
       (e.g. if someone requests an update to a non-existing commodity)
    -- it evaluates and determines remedies for any side effects
       incidental to the pending change

6. SideEffect
  - a dedicated construct for side effects and related remedies
  - the key benefit of the construct is clean code

7. CommodityTreeLoader
  - responsible for loading any subset of the tariff db commodity tree
    into a CommodityCollection (up to a chapter level)
  - see notes on workfow below for more detail

TP-803 WORKFLOW
With the above in mind, the intended workflow that TP-803 envisions
(parts of which are implemented elsewhere) is the following:
1. An incoming Taric envelope is parsed selectively to isolate commodity changes
  - the initial input can in theory be anythging else, e.g. a spreadsheet
2. The existing commodity tree in the database is loaded into a CommodityCollection
  using the CommodityTreeLoader (chapter by chapter)
3. The pending commodity changes are wrapped in CommodityChange instances
  - side effects are detected at this stage
  - this involves collection updates, taking "before" and "after" snapshots,
    plus probing for any related records that might be affected by the change
  - any required remedies are stored in the instance's SideEffects list
4. The collection is updated with the pending changes represented by these objects
5. At this point we have everything we need in order to be able to write
  changes to the tariff db that have the intended effect on the tree hierarchy
  and remedy any side effects on any related records caught up in the change
  - this is picked up by a separate handler downstream (see scope below)

TP-803 SCOPE
All of the above can be viewed simply as a holding bay slash decision engine;
no action is taken until the pending changes to commodities and related records
are ultimately applied as transactions in a workbasket downstream.
This write stage is the the conern of import handlers
and is implemented as a separate feature (see TP-931).
"""
