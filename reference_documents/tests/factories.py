import string
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import factory
from factory.fuzzy import FuzzyDateTime
from factory.fuzzy import FuzzyDecimal
from factory.fuzzy import FuzzyInteger
from factory.fuzzy import FuzzyText

from common.util import TaricDateRange
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.models import ReferenceDocumentVersionStatus


class ReferenceDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.ReferenceDocument"

    area_id = FuzzyText("", 2, "", string.ascii_uppercase)
    created_at = FuzzyDateTime(datetime(2008, 1, 1, tzinfo=UTC), datetime.now())
    title = FuzzyText("Reference Document for ", 5, "", string.ascii_uppercase)


class ReferenceDocumentVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.ReferenceDocumentVersion"

    created_at = FuzzyDateTime(datetime(2020, 1, 1, tzinfo=UTC), datetime.now())
    updated_at = FuzzyDateTime(datetime(2020, 1, 1, tzinfo=UTC), datetime.now())
    version = FuzzyDecimal(1.0, 5.0, 1)
    published_date = FuzzyDateTime(datetime(2022, 1, 1, tzinfo=UTC), datetime.now())
    entry_into_force_date = FuzzyDateTime(
        datetime(2022, 1, 1, tzinfo=UTC),
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
        FuzzyDateTime(
            datetime.now() + timedelta(days=-(365 * 2)),
            datetime.now() + timedelta(days=-365),
        ),
        FuzzyDateTime(datetime.now() + timedelta(days=-364), datetime.now()),
    )

    class Params:
        valid_between_current = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=-200),
                upper=datetime.now() + timedelta(days=165),
            ),
        )
        valid_between_current_open_ended = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=-200),
                upper=None,
            ),
        )
        valid_between_in_past = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=-375),
                upper=datetime.now() + timedelta(days=-10),
            ),
        )
        valid_between_in_future = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=10),
                upper=datetime.now() + timedelta(days=375),
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
        FuzzyDateTime(
            datetime.now() + timedelta(days=-(365 * 2)),
            datetime.now() + timedelta(days=-365),
        ),
        FuzzyDateTime(datetime.now() + timedelta(days=-364), datetime.now()),
    )

    class Params:
        valid_between_current = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=-200),
                upper=datetime.now() + timedelta(days=165),
            ),
        )
        valid_between_current_open_ended = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=-200),
                upper=None,
            ),
        )
        valid_between_in_past = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=-375),
                upper=datetime.now() + timedelta(days=-10),
            ),
        )
        valid_between_in_future = factory.Trait(
            valid_between=TaricDateRange(
                lower=datetime.now() + timedelta(days=10),
                upper=datetime.now() + timedelta(days=375),
            ),
        )


class AlignmentReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.AlignmentReport"

    created_at = FuzzyDateTime(datetime(2020, 1, 1, tzinfo=UTC), datetime.now())
    reference_document_version = factory.SubFactory(ReferenceDocumentVersionFactory)


class AlignmentReportCheckFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reference_documents.AlignmentReportCheck"

    created_at = FuzzyDateTime(datetime(2020, 1, 1, tzinfo=UTC), datetime.now())
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
