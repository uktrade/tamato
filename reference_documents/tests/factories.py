import string
from datetime import date
from datetime import datetime
from datetime import timedelta
from random import randint

import factory
from factory.fuzzy import FuzzyDecimal
from factory.fuzzy import FuzzyInteger
from factory.fuzzy import FuzzyText

from common.util import TaricDateRange
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.models import ReferenceDocumentVersionStatus


def get_random_date(start_date, end_date):
    days_diff = abs((end_date - start_date).days)
    return start_date + timedelta(days=randint(0, days_diff))


class ReferenceDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.ReferenceDocument"

    area_id = FuzzyText("", 2, "", string.ascii_uppercase)
    created_at = get_random_date(
        date(2008, 1, 1),
        date.today(),
    )
    title = FuzzyText("Reference Document for ", 5, "", string.ascii_uppercase)


class ReferenceDocumentVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.ReferenceDocumentVersion"

    created_at = get_random_date(datetime(2020, 1, 1), datetime.now())
    updated_at = get_random_date(datetime(2020, 1, 1), datetime.now())
    version = FuzzyDecimal(1.0, 5.0, 1)
    published_date = get_random_date(datetime(2022, 1, 1), datetime.now())
    entry_into_force_date = get_random_date(
        datetime(2022, 1, 1),
        datetime.now(),
    )

    reference_document = factory.SubFactory(ReferenceDocumentFactory)

    status = ReferenceDocumentVersionStatus.EDITING

    class Params:
        in_review = factory.Trait(
            status=ReferenceDocumentVersionStatus.IN_REVIEW,
        )
        published = factory.Trait(
            status=ReferenceDocumentVersionStatus.PUBLISHED,
        )
        editing = factory.Trait(
            status=ReferenceDocumentVersionStatus.EDITING,
        )


class PreferentialRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.PreferentialRate"

    commodity_code = FuzzyText(length=6, chars=string.digits, suffix="0000")

    duty_rate = FuzzyText(length=2, chars=string.digits, suffix="%")

    order = FuzzyInteger(0, 100, 1)

    reference_document_version = factory.SubFactory(ReferenceDocumentVersionFactory)

    valid_between = TaricDateRange(
        get_random_date(
            date.today() + timedelta(days=-(365 * 2)),
            date.today() + timedelta(days=-365),
        ),
        get_random_date(
            date.today() + timedelta(days=-364),
            date.today(),
        ),
    )

    class Params:
        valid_between_current = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-200),
                date.today() + timedelta(days=165),
            ),
        )
        valid_between_current_open_ended = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-200),
                None,
            ),
        )
        valid_between_in_past = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-375),
                date.today() + timedelta(days=-10),
            ),
        )
        valid_between_in_future = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=10),
                date.today() + timedelta(days=375),
            ),
        )


class PreferentialQuotaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.PreferentialQuota"

    commodity_code = FuzzyText(length=6, chars=string.digits, suffix="0000")

    quota_duty_rate = FuzzyText(length=2, chars=string.digits, suffix="%")

    quota_order_number = FuzzyText(prefix="054", length=3, chars=string.digits)

    volume = FuzzyDecimal(100.0, 10000.0, 1)

    coefficient = None

    main_quota = None

    measurement = "tonnes"
    order = FuzzyInteger(0, 100, 1)
    reference_document_version = factory.SubFactory(ReferenceDocumentVersionFactory)

    valid_between = TaricDateRange(
        get_random_date(
            date.today() + timedelta(days=-(365 * 2)),
            date.today() + timedelta(days=-365),
        ),
        get_random_date(
            date.today() + timedelta(days=-364),
            date.today(),
        ),
    )

    class Params:
        valid_between_current = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-200),
                date.today() + timedelta(days=165),
            ),
        )
        valid_between_current_open_ended = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-200),
                None,
            ),
        )
        valid_between_in_past = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-375),
                date.today() + timedelta(days=-10),
            ),
        )
        valid_between_in_future = factory.Trait(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=10),
                date.today() + timedelta(days=375),
            ),
        )


class AlignmentReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.AlignmentReport"

    created_at = get_random_date(date(2020, 1, 1), date.today())
    reference_document_version = factory.SubFactory(ReferenceDocumentVersionFactory)


class AlignmentReportCheckFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.AlignmentReportCheck"

    created_at = get_random_date(date(2020, 1, 1), date.today())
    alignment_report = factory.SubFactory(AlignmentReportFactory)

    check_name = FuzzyText(
        prefix="SomeClassName ",
        length=5,
        chars=string.ascii_uppercase,
    )

    status = (AlignmentReportCheckStatus.FAIL,)

    message = FuzzyText(
        prefix="Some Random Message ",
        length=5,
        chars=string.ascii_uppercase,
    )

    preferential_quota = None
    preferential_rate = None

    class Params:
        with_quota = factory.Trait(
            preferential_quota=factory.SubFactory(PreferentialQuotaFactory),
        )
        with_rate = factory.Trait(
            preferential_rate=factory.SubFactory(PreferentialRateFactory),
        )
        passing = factory.Trait(
            status=AlignmentReportCheckStatus.PASS,
        )
        warning = factory.Trait(
            status=AlignmentReportCheckStatus.WARNING,
        )
