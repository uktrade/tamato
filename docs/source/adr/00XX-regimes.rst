XX. Regimes
===========

Date: 2022-03-16


Status
------

Current


Context
-------

A "tariff regime" is what we call a policy that defines a set of tariff
measures, rates or rules for the goods and countries that take part in them.
(Our users also refer to this as a "measure" this conflicts with a TARIC model
of the same name).

A free trade agreement or a band of the Generalised System of Preferences (GSP)
are both examples of tariff regimes.

Tariff regimes are the "unit of measure" at the 'entire nation' level of tariff
policy – one departmental team might be responsible for a single regime, or a
few. In general, regimes define not just the rates that apply today, but also
tomorrow and in several years time (e.g. the staging of a free trade agreement).

At the moment, TAP has no knowledge of tariff regimes. It is purely concerned
with low-level tariff measures and the specific rates that apply. It is the job
of the tariff managers to translate the rules defined by a tariff regime into
measures, manually.

So where a tariff regime might say, "the rate on all fruits is the UK MFN minus
3% per year of this agreement", at the moment TAP only can understand "at this
certain time, for this country, the rate on commodity code Y will be X".

By capturing the rules associated with tariff regimes as agreed around the
negotiating table and printed in the legal text, we can realise several
opportunities and efficiency savings:

1. We can apply automation to the process of tariff management, and remove
   several burdensome problems tariff managers currently will deal with.
2. We can provide higher-level information for analysis by policy teams, e.g. as
   a part of trade negotiations.
3. We can provide richer information on future tariffs to traders and services. 

As examples of some of the areas we can automate if we hold richer tariff
information:

* We can automatically create measures for an entire set of commodity codes.
* Where an FTA defines a staged reduction in tariffs over a number of years, we
  can record the intent of the FTA and have TAP compute the correct rate
  automatically, including if it relies on another rate (e.g. 5% of the UKGT).
* Where an FTA defines a preferential rate higher than the UKGT, but we decide
  to never charge higher than the UKGT, TAP can handle this itself.
* Where the GSP defines a rule like “3.5% reduction, or 30% reduction if UKGT
  has a specific duty component” we can calculate this automatically, and adjust
  it if the UKGT changes.
* We can automatically apply rules about nuisance tariffs (e.g. nothing <2%),
  and auto change measures if we decide to increase our nuisance threshold.

Because tariff regimes are not part of the information required by our current
data consumers, we can safely innovate in this area without any legacy
restrictions.


Use cases
---------

Here we list some specific regimes that are in live use in order to show the
sort of complexity that a new data structure will have to contend with.


Home Office Drug Control
~~~~~~~~~~~~~~~~~~~~~~~~

The drug control regime specifies that on certain long and disparate list of
commodity codes, import is not allowed without presentation of a certificate.
This is quite typical of an import or export control regime.

**Home Office Drug Control**

* Regulation: X2100302
* Geography: Erga Omnes
* Conditions: With cert N123, import allowed. Else: Import not allowed.
* Codes: 0102 00 00 00, 0103 00 00 00, ...

At the moment this is implemented with one individual measure for each commodity
code, so our users have to create one measure for every code.

The measures are only linked together through their use of the same regulation.
Any change to the regime as a whole requires changing all of the measures.

What sort of changes are likely? Adding and removing commodity codes from the
list of affected codes is likely. Adding exemptions or new conditions to the
list is also likely. The latter case again involves changing every measure.


Japan Free Trade Agreement
~~~~~~~~~~~~~~~~~~~~~~~~~~

The FTA regime specifies preferential treatment for imports from Japan. Many
quotas are at 0% but it also defines some "categories" of rates that are staged.
There are also some quotas.

**Japan FTA**

* Regulation: Free Trade Agreement Between the United Kingdom of Great Britain
  and Northern Ireland and the Republic of Japan
* Geography: Japan
* Agreement starts: 1st Feb 2021
* Basic rates:

    * Codes: 0102 00 00 00, 0103 00 00 00, …
    * Rate: 0%
    
* Category 1, etc.:

    * Codes: 0201 00 00 00, …
    * Rate: The MFN rate minus 5% per year of the agreement

* Quota 051040:

    * Codes: …
    * Annual volume: …
    * Rate: 0%

Here there are a few things that are beyond the capability of the current model.
The rate for certain categories is a rule that depends on another rate, and also
changes over time. At the moment, that dependency and time information is not
stored – measures only contain a specific rate for a specific date range.


Generalised System of Preferences (GSP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GSP introduces preferences for developing countries that are similar in
structure to the FTA above. 

There are lists of countries that benefit from three different types of
preference: the "general" list, the "enhanced" list and the "least developed
countries" list. Countries are added and removed from the lists over time,
especially when we sign new other agreements with them, or in response to bad
behaviour.

Some GSP rates are seasonal i.e. they are only available at certain times of the
year.

**Generalised System of Preferences**

* Regulation: P2100302
* General list: 

    * Codes: 0102 00 00 00, 0103 00 00 00, ...
    * Rate: The UKGT minus 3.5% if it is a specific duty or minus 30% if it is
      ad valorem, with no less than 2% as a result
    * Countries: India, Indonesia, Tajikistan
    * Seasons:

        * Codes: 0102 00 00 00, ...
        * Start day/month: 1st Jan
        * End day/month: 31st Apr

In this example we see that one regime can again contain potentially many
separate categories, and these categories can vary substantially (i.e. it's not
just commodity codes). We also see that there is a "sub-category" of seasons which
overrides treatment for certain codes.

Seasonal dates (i.e. day and month without a year) are also used. The duty rate
is also considerably more complex.


Universal exemptions
~~~~~~~~~~~~~~~~~~~~

The universal exemption regime adds a magic exemption code (999L) to a large
list of pre-existing import and export control regimes. For a limited period of
time, traders should be able to use the exemption code and have all other
requirements from the regime ignored. Essentially, this is adding a new
time-limited exemption on about ~40 other control regimes.

**Universal exemptions**

* Regimes: Home Office Drug Control, CITES, ...
* Add condition: with cert 999L, import allowed
* Start date: 22nd Jan 2022
* End date: 30th Sept 2023

This is challenging to implement manually because existing control measures have
to be end-dated, recreated with the exemption present for a limited time, and
then ended and re-added with their original conditions.

This is obviously hugely error-prone and results in about 120,000 individual
tariff changes. It also means that subsequent changes to those regimes will
require users to manually remember to handle the 999L conditions, making it much
more difficult to modify them.

This example introduces an idea that some regimes will need to modify others,
even though they are logically separate in the minds of our users, and the
system will need to be able to compose the result into a TARIC3 output itself.


Veterinary controls
~~~~~~~~~~~~~~~~~~~

The Veterinary controls regime uses a number of standard entry documents (called
CHEDs) to control import of plans, animals and derived goods such as feed. A
commodity code can be subject to none, some or all of the CHED requirements and
traders can use any of the CHED certificates to complete an import.

**Veterinary controls**

* Geography: Erga omnes, excluding European Union
* Condition: With no certificate, import not allowed.
* CHED-A:

    * Codes: 0102 00 00 00, ...
    * Add condition: With certificate C640, import allowed

* CHED-P:

    * Codes: 0201 00 00 00, ...
    * Add condition: With certificate N853, import allowed

* CHED-D:

    * Codes: 0201 00 70 99, ...
    * Add condition: With certificate C678, import allowed

This adds conditions based on membership of categories (so a code could be in
more than one category). The system will work out what measures are required and
where in the hierarchy they need to be placed.

For example, in the case of the last two categories, the code for CHED-D is a
child code of a code in CHED-P, so the system will need to notice that and add a
measure with both certificate conditions on that code and only the CHED-P
certificate on all sibling codes to avoid ME32.


Required capabilities
---------------------

We need to store all of this complexity and also successfully use it to output a
TARIC3-compliant database. There are a number of steps involved in this:

1. **Store**: record the sort of regimes above in a structured format
2. **Resolve**: consider the entire set of regime data, and work out what TARIC3
   measures should therefore be present

In the context of users making a change to the regimes:

3. **Compare**: examine the existing state of TARIC3 and output diffs against
   that state to update it to be in line with the resolved data

In the latter step, we can either keep our own store of TARIC3 data and update
it, or keep an "ephemeral" store based on what should have been output before a
regime was modified. The former is probably easier and more robust in the face
of bugs.


New capabilities for storing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We would need to be able to store:

* Seasonal dates: specifying just day and month dates
* Composition: 
* Explosion: specifying whole lists of data where there are currently only single items permitted
* Composition: specifying some data at a high level, and 