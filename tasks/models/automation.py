import logging

from django.db import models
from polymorphic.models import PolymorphicModel

logger = logging.getLogger(__name__)


class StateChoices(models.TextChoices):
    """Defines the set of states an Automation instance may be in."""

    CAN_RUN = "CAN_RUN", "Can run"
    """A TaskAutomation instance's `run()` method may be called."""

    RUNNING = "RUNNING", "Running"
    """A TaskAutomation instance is currently running an automation activity."""

    DONE = "DONE", "Done"
    """A TaskAutomation instance is in some done and isn't expected to run
    again."""

    ERRORED = "ERRORED", "Errored"
    """A TaskAutomation instance is in an errored state."""


# TODO
# from django.db.models import Manager
# from django.utils.module_loading import import_string
#
# class AutomationManager(Manager):
#    def create(self, automation_class_name, task) -> type:
#        try:
#            automation_cls = import_string(automation_class_name)
#            automation_obj = automation_cls(task=task)
#            automation_obj.save()
#        except ImportError:
#            """TODO"""
#            pass
#        return automation_obj


class Automation(PolymorphicModel):
    """
    Base class inherited by models that define and encapsulate task automation
    capability.

    Subclasses should define their own class attributes for:
    - name
    - help_text

    Subclasses should also implement the 'run()' method, which will be called to
    perform a task's automation step. Implementors should consider constraints
    and possible error conditions when performing task automation. The 'run()'
    method should return a URL route name to a results view that presents
    success or failure information.
    """

    name = "Task automation"
    """The name used in the UI to identify this automation. Subclasses should
    override this attribute."""

    help_text = "Automates a task."
    """The help text used in the UI to describe what this automation does. This
    helps users to select the correct automation for their tasks when
    constructing workflow templates. Subclasses should override this
    attribute."""

    task = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
    )
    """The Task instance associate with this automation."""

    def get_state(self) -> StateChoices:
        """
        Returns a StateChoices element representing the current state of this
        instance.

        It's implicitly assumed that an Automation instance can be in multiple
        states.
        """
        raise NotImplemented()

    def rendered_state(self) -> str:
        """
        Return a valid rendered block of HTML for inclusion in a web page. The
        block is used to present current state and action options (e.g. URLs
        that navigate to the automation's forms, etc).

        The returned HTML may include anchors and other valid elements that
        format content.
        """

        return """<p class="govuk-body">Automate subclasses should override this.</p>"""
