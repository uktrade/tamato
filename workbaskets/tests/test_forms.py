import pytest

from common.tests import factories
from tasks.models import TaskAssignee
from workbaskets import forms
from workbaskets.validators import tops_jira_number_validator

pytestmark = pytest.mark.django_db


def test_workbasket_create_form_valid_data():
    """Test that WorkbasketCreateForm is valid when required fields in data."""
    data = {"title": "123", "reason": "testing testing"}
    form = forms.WorkbasketCreateForm(data=data)

    assert form.is_valid()


def test_workbasket_create_form_invalid_data():
    """Test that WorkbasketCreateForm is not valid when required fields not in
    data."""

    form = forms.WorkbasketCreateForm(data={})
    assert not form.is_valid()
    assert "This field is required." in form.errors["title"]
    assert "This field is required." in form.errors["reason"]

    form = forms.WorkbasketCreateForm(data={"title": "abc", "reason": "test"})
    assert not form.is_valid()
    assert tops_jira_number_validator.message in form.errors["title"]

    factories.WorkBasketFactory(title="123321")
    form = forms.WorkbasketCreateForm(data={"title": "123321", "reason": "test"})
    assert not form.is_valid()
    assert "A workbasket with this title already exists" in form.errors["title"]


def test_selectable_objects_form():
    """Test that the SelectableObjectsForm creates a SelectableObjectField for
    each item passed to it, and the class methods and properties provide the
    expected data for the item."""
    measures = factories.MeasureFactory.create_batch(5)
    form = forms.SelectableObjectsForm(initial={}, prefix=None, objects=measures)
    # grab a list of the ids tacked on to the end of the field name, as this
    # should be the pk of the measure.
    form_fields_keys = [str.partition("_")[2] for str in form.fields.keys()]
    measure_pks = [str(measure.pk) for measure in measures]

    # Check that the fields in the form has the same length as the measures we made.
    assert len(form.fields) == 5
    # Check that the ids added to the end of the field names, match the measure pks.
    assert form_fields_keys == measure_pks

    for item in measures:
        # Check that the field name class method returns the right name.
        assert (
            forms.SelectableObjectsForm.field_name_for_object(
                measures[measures.index(item)],
            )
            == f"selectableobject_{item.pk}"
        )
        # Check that the id class method returns the right id.
        assert (
            forms.SelectableObjectsForm.object_id_from_field_name(
                list(form.fields.keys())[measures.index(item)],
            )
            == measure_pks[measures.index(item)]
        )
        # Check that the fields are of SelectableObjectField type
        assert (
            type(form.fields[f"selectableobject_{item.pk}"])
            is forms.SelectableObjectField
        )

    # Check that the cleaned_data_no_prefix property returns a list of the data with no prefixes.
    form.cleaned_data = {
        f"selectableobject_{measure_pks[0]}": True,
        f"selectableobject_{measure_pks[1]}": True,
        f"selectableobject_{measure_pks[2]}": True,
        f"selectableobject_{measure_pks[3]}": False,
        f"selectableobject_{measure_pks[4]}": False,
    }
    # The cleaned_data_no_prefix property is created using cleaned_data, so providing cleaned_data should
    # create the object for us, so we just need to check it matches what we expect.
    assert form.cleaned_data_no_prefix == {
        measure_pks[0]: True,
        measure_pks[1]: True,
        measure_pks[2]: True,
        measure_pks[3]: False,
        measure_pks[4]: False,
    }
    # Check that the fields are of SelectableObjectField type
    for item in measures:
        assert (
            type(form.fields[f"selectableobject_{item.pk}"])
            is forms.SelectableObjectField
        )


def test_workbasket_compare_form_valid():
    data = {
        "data": (
            "2909500090\t0.000% + 2.000 GBP / 100 kg\t20/05/2021\t31/08/2024\n"
            "2909500090\t0.000%\t\t31/08/2024\n"
            "3945875\tfoo bar\t438573\t\n"  # line with nonsense data
        ),
    }
    form = forms.WorkbasketCompareForm(data=data)
    assert form.is_valid()
    assert form.cleaned_data


def test_workbasket_compare_form_invalid():
    data = {
        "data": (
            "2909500090\t0.000% + 2.000 GBP / 100 kg\t20/05/2021\t31/08/2024\n"
            "290950<>0090\t0.000%\t\t31/08/2024\n"
            "3945875\tfoo bar\t438573\t\n"  # line with nonsense data
        ),
    }
    form = forms.WorkbasketCompareForm(data=data)
    assert not form.is_valid()
    assert "Only symbols" in form.errors["data"][0]


def test_workbasket_assign_users_form_assigns_users(rf, valid_user, user_workbasket):
    request = rf.request()
    request.user = valid_user
    users = factories.UserFactory.create_batch(2, is_superuser=True)
    data = {
        "users": users,
        "assignment_type": TaskAssignee.AssignmentType.WORKBASKET_WORKER,
    }

    form = forms.WorkBasketAssignUsersForm(
        request=request,
        workbasket=user_workbasket,
        data=data,
    )
    assert form.is_valid()

    task = factories.TaskFactory.create(workbasket=user_workbasket)
    form.assign_users(task=task)
    for user in users:
        assert TaskAssignee.objects.get(user=user, task=task)


def test_workbasket_assign_users_form_required_fields(rf, valid_user, user_workbasket):
    request = rf.request()
    request.user = valid_user

    form = forms.WorkBasketAssignUsersForm(
        request=request,
        workbasket=user_workbasket,
        data={},
    )
    assert not form.is_valid()
    assert f"Select one or more users to assign" in form.errors["users"]
    assert f"Select an assignment type" in form.errors["assignment_type"]


def test_workbasket_unassign_users_form_unassigns_users(
    rf,
    valid_user,
    user_workbasket,
):
    request = rf.request()
    request.user = valid_user
    assignees = factories.TaskAssigneeFactory.create_batch(
        2,
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
        task__workbasket=user_workbasket,
    )
    data = {
        "assignees": assignees,
    }

    form = forms.WorkBasketUnassignUsersForm(
        request=request,
        workbasket=user_workbasket,
        data=data,
    )
    assert form.is_valid()

    form.unassign_users()
    for assignee in assignees:
        assignee.refresh_from_db()
        assert not assignee.is_assigned


def test_workbasket_unassign_users_form_required_fields(
    rf,
    valid_user,
    user_workbasket,
):
    request = rf.request()
    request.user = valid_user

    form = forms.WorkBasketUnassignUsersForm(
        request=request,
        workbasket=user_workbasket,
        data={},
    )
    assert not form.is_valid()
    assert f"Select one or more users to unassign" in form.errors["assignees"]


def test_workbasket_comment_create_form(assigned_workbasket):
    """Tests that `WorkBasketCommentCreateForm` creates a comment for a given
    workbasket and user."""
    expected_content = "Test comment."
    data = {"content": expected_content}
    form = forms.WorkBasketCommentCreateForm(data=data)
    assert form.is_valid()

    user = assigned_workbasket.author
    comment = form.save(user=user, workbasket=assigned_workbasket)
    assert comment.author == user
    assert comment.task == assigned_workbasket.tasks.get()
    assert expected_content in comment.content


markdown_and_html: list[tuple[str, str]] = [
    ("# Heading", "<h1>Heading</h1>"),
    ("> Blockquote", "<blockquote>\n<p>Blockquote</p>\n</blockquote>"),
    ("**Bold**", "<p><strong>Bold</strong></p>"),
    ("*Italic*", "<p><em>Italic</em></p>"),
    ("1. List", "<ol>\n<li>List</li>\n</ol>"),
    ("- List", "<ul>\n<li>List</li>\n</ul>"),
    (f"[Link](https://example.org)", "<p>Link</p>"),
    ("<a href='www.example.org'>Link</a>", "<p>Link</p>"),
    (f"![Image](path/to/file)", "<p></p>"),
    ("<img src='path/to/image'></img>", "<p></p>"),
    ("<script>alert('Test')</script>", "alert('Test')"),
]


@pytest.mark.parametrize(
    "markdown, html",
    markdown_and_html,
)
def test_workbasket_comment_create_form_cleans_content(
    markdown,
    html,
):
    """Tests that `WorkBasketCommentCreateForm` converts Markdown to sanitised
    HTML."""
    data = {"content": markdown}
    form = forms.WorkBasketCommentCreateForm(data=data)
    assert form.is_valid()
    assert form.cleaned_data["content"] == html


@pytest.mark.parametrize(
    "markdown, html",
    markdown_and_html,
)
def test_workbasket_comment_update_form_cleans_content(
    markdown,
    html,
):
    """Tests that `WorkBasketCommentUpdateForm` converts Markdown to sanitised
    HTML."""
    comment = factories.CommentFactory.create()
    data = {"content": markdown}
    form = forms.WorkBasketCommentCreateForm(instance=comment, data=data)
    assert form.is_valid()
    assert form.cleaned_data["content"] == html


def test_workbasket_comment_update_form():
    """Tests that `WorkBasketCommentUpdateForm` updates a comment's content."""
    comment = factories.CommentFactory.create()
    content = "Edited comment."
    data = {"content": content}
    form = forms.WorkBasketCommentUpdateForm(instance=comment, data=data)
    assert form.is_valid()
    form.save()
    comment.refresh_from_db()
    assert content in comment.content
