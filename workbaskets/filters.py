from django.contrib.postgres.search import SearchRank
from django.contrib.postgres.search import SearchVector
from django.db.models import Case
from django.db.models import FloatField
from django.db.models import Q
from django.db.models import Value
from django.db.models import When

from common.filters import TamatoFilterBackend
from common.filters import TamatoFilterMixin


class WorkBasketFilterMixin(TamatoFilterMixin):
    search_fields = ("title", "reason")

    def search_queryset(self, queryset, search_term):
        """
        Filters the queryset to results with `search_fields` (including PK)
        containing or matching the `search_term`.

        Results are ordered first by relevancy then by PK to favour newer
        objects in the event of a tied rank value. Exact search term matches are
        therefore prioritised over partial substring matches.

        The search rank is normalised to penalise longer documents and those
        with a high unique word count, improving relevance scoring.
        """
        NORMALISATION_LOG_LENGTH = 1
        NORMALISATION_UNIQUE_WORDS = 8

        search_term = self.get_search_term(search_term)
        search_vector = SearchVector(*self.search_fields)
        search_rank = SearchRank(
            search_vector,
            search_term,
            normalization=Value(NORMALISATION_LOG_LENGTH).bitor(
                Value(NORMALISATION_UNIQUE_WORDS),
            ),
        )

        vector_queryset = queryset.annotate(search=search_vector)

        exact_match_query = Q(search=search_term)
        partial_match_query = Q(search__icontains=search_term)
        query = exact_match_query | partial_match_query
        try:
            pk_query = Q(pk=int(search_term))
            query |= pk_query
            search_rank = Case(
                When(pk=search_term, then=1),
                default=search_rank,
                output_field=FloatField(),
            )
        except ValueError:
            pass

        return (
            vector_queryset.annotate(
                rank=search_rank,
            )
            .filter(query)
            .order_by("-rank", "-pk")
        )


class WorkBasketAutoCompleteFilterBackEnd(TamatoFilterBackend, WorkBasketFilterMixin):
    pass
