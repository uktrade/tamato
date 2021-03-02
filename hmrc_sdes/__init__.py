"""
Provides the ability to communicate with HMRC's Secure Data Exchange Service
(SDES).

When TaMaTo wants to send tariff updates to CDS, it must first make an
:class:`~taric.models.Envelope` file available from an SFTP endpoint. It must
then notify SDES via an HTTPS API that a file is ready to be downloaded. This
module makes available the API client library to make the call.

More information about SDES is available from `the HMRC developer hub
<https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/secure-data-exchange-notifications/1.0>`_.
"""
