Interpretation of dates
-----------------------

Dates are an important source of information in the TARIC system. Handling these
dates is critical to determine whether or not data is applicable at a given
date.

Different types
^^^^^^^^^^^^^^^

There are three different types of dates, as follows:

- explicit dates: these are fully specified dates, for example 01/01/1994
- implicit dates: these are sent as "spaces" and refer to other entities
- open end dates: these are sent as "spaces" and indicate that they are open ended

Start dates
^^^^^^^^^^^

All start dates are explicit. The only exception is the measure start date; if
it is the same as the regulation start date, it should be considered as an
implicit date from a validation point of view.

End dates
^^^^^^^^^

All end dates can be explicit.

Measures
""""""""

The end date can be implicit in that the real end
date must be fetched from its generating regulation.

Modification regulation
"""""""""""""""""""""""

The end date can be implicit in that the real end date must be fetched from the
related base regulation.

Other entities
""""""""""""""

End dates for other entities can be open ended.


