from django.db.transaction import atomic
from polymorphic.query import PolymorphicQuerySet


class TrackedModelCheckQueryset(PolymorphicQuerySet):
    def delete(self):
        """
        Delete, modified to workaround a python bug that stops delete from
        working when some fields are ByteFields.

        Details:

        Using .delete() on a query with ByteFields does not work due to a python bug:
          https://github.com/python/cpython/issues/95081
        >>> TrackedModelCheck.objects.filter(
            model__transaction__workbasket=workbasket_pk,
            ).delete()

         File /usr/local/lib/python3.8/copy.py:161, in deepcopy(x, memo, _nil)
            159 reductor = getattr(x, "__reduce_ex__", None)
            160 if reductor is not None:
        --> 161     rv = reductor(4)
            162 else:
            163     reductor = getattr(x, "__reduce__", None)

        TypeError: cannot pickle 'memoryview' object

        Work around this by setting the bytefields to None and then calling delete.
        """
        with atomic():
            self.update(content_hash=None)
            return super().delete()
