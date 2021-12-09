import pytest

from commodities import models
from commodities import serializers
from common.tests import factories
from common.validators import UpdateType
from importer.namespaces import TARIC_RECORD_GROUPS
from measures.models import Measure
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_goods_nomenclature_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GoodsNomenclatureFactory,
        serializers.GoodsNomenclatureSerializer,
    )


def test_goods_nomenclature_description_importer(
    imported_fields_match,
):
    assert imported_fields_match(
        factories.GoodsNomenclatureDescriptionFactory,
        serializers.GoodsNomenclatureDescriptionSerializer,
        dependencies={
            "described_goods_nomenclature": factories.GoodsNomenclatureFactory,
        },
    )


def test_goods_nomenclature_origin_importer(
    update_type,
    date_ranges,
    imported_fields_match,
):
    origin = factories.GoodsNomenclatureFactory.create(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.big,
        origin__derived_from_goods_nomenclature__valid_between=date_ranges.adjacent_earlier_big,
    )
    good = factories.GoodsNomenclatureFactory.create(
        update_type=UpdateType.CREATE.value,
        origin=None,
    )

    assert imported_fields_match(
        factories.GoodsNomenclatureOriginFactory,
        serializers.GoodsNomenclatureOriginSerializer,
        dependencies={
            "derived_from_goods_nomenclature": origin,
            "new_goods_nomenclature": good,
        },
    )

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    origins = models.GoodsNomenclatureOrigin.objects.filter(
        new_goods_nomenclature=db_good,
    ).latest_approved()
    if update_type == UpdateType.DELETE:
        assert not origins.exists()
    else:
        assert origins.get().derived_from_goods_nomenclature == origin


def test_goods_nomenclature_successor_importer_create(
    run_xml_import,
    date_ranges,
):

    good = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.normal,
    )
    successor = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.adjacent_later,
    )

    run_xml_import(
        lambda: factories.GoodsNomenclatureSuccessorFactory.build(
            replaced_goods_nomenclature=good,
            absorbed_into_goods_nomenclature=successor,
            update_type=UpdateType.CREATE.value,
        ),
        serializers.GoodsNomenclatureSuccessorSerializer,
    )

    db_link = models.GoodsNomenclatureSuccessor.objects.get(
        replaced_goods_nomenclature__sid=good.sid,
    )
    assert db_link

    db_good = models.GoodsNomenclature.objects.get(sid=good.sid)
    assert db_good.successors.get() == successor


def test_goods_nomenclature_successor_importer_delete(
    run_xml_import,
    date_ranges,
):
    good = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.normal,
    )
    successor = factories.GoodsNomenclatureFactory(
        update_type=UpdateType.CREATE.value,
        valid_between=date_ranges.adjacent_later,
    )
    factories.GoodsNomenclatureSuccessorFactory(
        replaced_goods_nomenclature=good,
        absorbed_into_goods_nomenclature=successor,
        update_type=UpdateType.CREATE.value,
    )

    updated_good = factories.GoodsNomenclatureFactory(
        sid=good.sid,
        item_id=good.item_id,
        suffix=good.suffix,
        version_group=good.version_group,
        update_type=UpdateType.UPDATE.value,
        valid_between=date_ranges.no_end,
    )

    run_xml_import(
        lambda: factories.GoodsNomenclatureSuccessorFactory.build(
            replaced_goods_nomenclature=updated_good,
            absorbed_into_goods_nomenclature=successor,
            update_type=UpdateType.DELETE.value,
        ),
        serializers.GoodsNomenclatureSuccessorSerializer,
    )

    db_link = models.GoodsNomenclatureSuccessor.objects.filter(
        replaced_goods_nomenclature__sid=good.sid,
    )
    assert not db_link.latest_approved().exists()
    assert db_link.latest_deleted().exists()


def test_goods_nomenclature_indent_importer(imported_fields_match):
    db_indent = imported_fields_match(
        factories.GoodsNomenclatureIndentFactory,
        serializers.GoodsNomenclatureIndentSerializer,
        dependencies={
            "indented_goods_nomenclature": factories.SimpleGoodsNomenclatureFactory(
                item_id="1100000000",
            ),
        },
    )

    assert db_indent.indent == 0


def test_footnote_association_goods_nomenclature_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteAssociationGoodsNomenclatureFactory,
        serializers.FootnoteAssociationGoodsNomenclatureSerializer,
        dependencies={
            "goods_nomenclature": factories.GoodsNomenclatureFactory,
            "associated_footnote": factories.FootnoteFactory,
        },
    )


@pytest.mark.parametrize(
    ("measure_validity", "is_affected", "update_type"),
    (
        ("adjacent_later", True, UpdateType.DELETE),  # should be deleted
        (
            "overlap_normal_earlier",
            True,
            UpdateType.UPDATE,
        ),  # should have a new start_date
        ("overlap_normal", True, UpdateType.UPDATE),  # should have a new end date
        ("starts_with_normal", False, None),  # should not be affected
    ),
    ids=("future", "earlier", "current", "shortlived"),
)
def test_correct_affected_measures_are_selected(
    run_xml_import,
    date_ranges,
    measure_validity,
    is_affected,
    update_type,
):
    """
    Asserts that the commodity importer handles preemptive measure transactions
    well.

    When commodity code changes are imported (e.g. from EU taric files),
    these changes may cause side effects in terms of business rule violations.
    This happens often for related measures. It is important to ensure
    that only the measures that should be changed are changed.
    For example, future and overlapping measures relative to the good's updated validity
    should be updated or deleted with preemptive transactions;
    however measures whose validity period remains contained
    within the good's updated validity should not be touched.

    For context, see `commodities.models.dc.SideEffects`
    """
    attrs = dict(
        item_id="1199102030",
        suffix="80",
    )

    good = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.no_end, **attrs
    )
    attrs.update(sid=good.sid)

    future_measure = factories.MeasureFactory(
        goods_nomenclature=good,
        valid_between=getattr(date_ranges, measure_validity),
    )

    imported_good = run_xml_import(
        lambda: factories.GoodsNomenclatureFactory.build(
            valid_between=date_ranges.normal, update_type=UpdateType.UPDATE, **attrs
        ),
        serializers.GoodsNomenclatureSerializer,
        TARIC_RECORD_GROUPS["commodities"],
        # Need a draft workbasket status so that the measure generated
        # as a side effect is ordered *after* the commodity it is on.
        WorkflowStatus.PROPOSED,
    )

    workbasket = imported_good.transaction.workbasket
    affected_measures = [
        model for model in workbasket.tracked_models.all() if type(model) == Measure
    ]
    affected_measure_sids = [measure.sid for measure in affected_measures]

    assert (future_measure.sid in affected_measure_sids) == is_affected
    if is_affected:
        assert affected_measures[0].update_type == update_type
