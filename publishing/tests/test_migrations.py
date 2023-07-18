import pytest


@pytest.mark.django_db()
def test_add_packaged_workbasket_to_loading_report(migrator):
    """Test that packaged workbaskets with a loading report are added to the
    newly-created `packaged_workbasket` field on the associated `LoadingReport`
    model before `loading_report` field is removed from `PackagedWorkBasket`."""

    # Before migration
    old_state = migrator.apply_initial_migration(
        ("publishing", "0007_crowndependenciespublishingtask_error"),
    )

    User = old_state.apps.get_model("auth", "User")
    WorkBasket = old_state.apps.get_model("workbaskets", "WorkBasket")
    PackagedWorkBasket = old_state.apps.get_model("publishing", "PackagedWorkBasket")
    LoadingReport = old_state.apps.get_model("publishing", "LoadingReport")

    # Create a packaged workbasket with an associated loading report
    user = User.objects.create(username="testuser")
    loading_report = LoadingReport.objects.create(
        file_name="report1",
        comments="test report1",
    )
    workbasket = WorkBasket.objects.create(author=user)
    packaged_workbasket = PackagedWorkBasket.objects.create(
        workbasket=workbasket,
        position="0",
        loading_report=loading_report,
    )

    # Apply migration
    new_state = migrator.apply_tested_migration(
        ("publishing", "0008_loadingreport_packaged_workbasket"),
    )

    PackagedWorkBasket = new_state.apps.get_model("publishing", "PackagedWorkBasket")
    LoadingReport = new_state.apps.get_model("publishing", "LoadingReport")

    # Ensure that packaged workbasket has been added to loading report
    packaged_workbasket = PackagedWorkBasket.objects.last()
    loading_report = LoadingReport.objects.last()
    assert loading_report.packaged_workbasket == packaged_workbasket
    assert packaged_workbasket.loadingreports.last() == loading_report

    migrator.reset()
