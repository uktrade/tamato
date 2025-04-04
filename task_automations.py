"""Task automations."""

AUTOMATIONS = [
    ("workbaskets.models.CreateWorkBasketAutomation", "Create workbasket"),
    ("workbaskets.models.EndDateMeasuresAutomation", "End-date measures"),
    ("workbaskets.models.RunRuleChecksAutomation", "Run business rule checks"),
]
"""
An iterable of two-tuples. Each tuple must contain a task Automation class in
dotted path notation and accompanying description.

The class name is used to identify and load the automation class, the
description is presented to users through the UI when selecting and associating
them with tasks.

Note that changing the localtion of automation classes, or removing them
altogther, will break any tasks that have been configured to use the automation.
"""
