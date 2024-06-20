from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from reference_documents.forms.ref_order_number_forms import (
    RefOrderNumberCreateUpdateForm,
)
from reference_documents.forms.ref_order_number_forms import (
    RefOrderNumberDeleteForm,
)
from reference_documents.models import RefOrderNumber
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumberCreateUpdateForm:
    def test_init(self):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            instance=pref_quota_order_number,
        )

        # it sets initial values
        assert (
            target.reference_document_version
            == pref_quota_order_number.reference_document_version
        )
        assert target.Meta.model == RefOrderNumber
        assert target.Meta.fields == [
            "quota_order_number",
            "coefficient",
            "main_order_number",
            "valid_between",
        ]

    def test_clean_coefficient_pass_valid(self):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        data = {
            "coefficient": "1.6",
        }

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            instance=pref_quota_order_number,
            data=data,
        )

        assert not target.is_valid()
        assert target.instance.coefficient == Decimal("1.6")

    def test_clean_coefficient_fail_invalid(self):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        data = {
            "coefficient": "zz",
        }

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            instance=pref_quota_order_number,
            data=data,
        )

        assert not target.is_valid()
        assert target.errors["coefficient"] == ["Coefficient is not a valid number"]

    def test_clean_coefficient_pass_blank(self):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        data = {
            "coefficient": "",
        }

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            instance=pref_quota_order_number,
            data=data,
        )

        assert not target.is_valid()
        assert "coefficient" not in target.errors.keys()

    def test_clean_coefficient_pass_not_provided(self):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        data = {}

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            instance=pref_quota_order_number,
            data=data,
        )

        assert not target.is_valid()
        assert "coefficient" not in target.errors.keys()

    def test_clean_quota_order_number_valid_adding(self):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        data = {
            "quota_order_number": "054333",
        }

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            data=data,
        )

        assert not target.is_valid()
        assert "quota_order_number" not in target.errors.keys()

    def test_clean_quota_order_number_invalid_already_exists_adding(self):
        pref_quota_order_number = factories.RefOrderNumberFactory(
            quota_order_number="054333",
        )

        data = {
            "quota_order_number": "054333",
        }

        target = RefOrderNumberCreateUpdateForm(
            pref_quota_order_number.reference_document_version,
            data=data,
        )

        assert not target.is_valid()
        assert "quota_order_number" in target.errors.keys()

    def test_clean_quota_order_number_invalid_order_number_adding(self):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory()

        data = {
            "quota_order_number": "zzaabb",
        }

        target = RefOrderNumberCreateUpdateForm(
            ref_doc_ver,
            data=data,
        )

        assert not target.is_valid()
        assert "quota_order_number" in target.errors.keys()

    def test_clean_coefficient_no_main_order(self):
        factories.RefOrderNumberFactory()
        ref_order_number = factories.RefOrderNumberFactory()

        data = {
            "order_number": ref_order_number.order_number,
            "coefficient": "1.0",
            "valid_between": ref_order_number.valid_between,
        }

        target = RefOrderNumberCreateUpdateForm(
            ref_order_number.reference_document_version,
            data=data,
        )

        target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean()
        assert (
            "If you provide a value for the coefficient you must also select a main order number"
            in str(ve.value)
        )

    def test_clean_main_order_no_coefficient(self):
        ref_doc_version = factories.ReferenceDocumentVersionFactory()
        pref_quota_order_number_main = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_version,
        )
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_version,
        )

        data = {
            "main_order_number_id": pref_quota_order_number_main.id,
            "quota_order_number": ref_order_number.order_number,
            "valid_between": ref_order_number.valid_between,
        }

        target = RefOrderNumberCreateUpdateForm(
            ref_order_number.reference_document_version,
            data=data,
        )

        target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean()

        assert (
            "If you select a main order number a coefficient must also be provided"
            in str(ve.value)
        )


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumberDeleteForm:
    def test_init(self):
        ref_order_number = factories.RefOrderNumberFactory()

        target = RefOrderNumberDeleteForm(
            instance=ref_order_number,
        )

        assert target.instance == ref_order_number
        assert target.Meta.fields == []
        assert target.Meta.model == RefOrderNumber

    def test_clean_with_child_records(self):
        pref_quota = factories.RefQuotaDefinitionFactory()

        target = RefOrderNumberDeleteForm(
            instance=pref_quota.ref_order_number,
            data={},
        )

        assert not target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean()

        expected_string = (
            f"Quota order number {pref_quota.ref_order_number} "
            f"cannot be deleted as it has associated preferential quotas."
        )

        assert expected_string in str(ve)

    def test_clean_with_no_child_records(self):
        ref_order_number = factories.RefOrderNumberFactory()

        target = RefOrderNumberDeleteForm(
            instance=ref_order_number,
            data={},
        )

        assert target.is_valid()
        target.clean()

        assert len(target.errors) == 0
