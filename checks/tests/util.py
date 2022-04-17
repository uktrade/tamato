from pytest_django.asserts import assertQuerysetEqual  # type: ignore

from checks.models import TransactionCheck


def assert_queryset(queryset, expected):
    assertQuerysetEqual(queryset, expected, transform=lambda o: o, ordered=False)


def assert_current(check, expect_current=True):
    assert_queryset(
        TransactionCheck.objects.filter(id=check.pk).current(),
        {check} if expect_current else {},
    )


def assert_fresh(check, expect_fresh=True):
    assert_queryset(
        TransactionCheck.objects.filter(id=check.pk).fresh(),
        {check} if expect_fresh else {},
    )
    assert_queryset(
        TransactionCheck.objects.filter(id=check.pk).stale(),
        {check} if not expect_fresh else {},
    )


def assert_requires_update(check, expect_requires_update=True):
    assert_queryset(
        TransactionCheck.objects.filter(id=check.pk).requires_update(
            expect_requires_update,
        ),
        {check},
    )
    assert_queryset(
        TransactionCheck.objects.filter(id=check.pk).requires_update(
            not expect_requires_update,
        ),
        {},
    )
