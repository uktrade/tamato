def envelope_checker(workbaskets, envelope):
    """Checks that the transactions in a workbasket have been correctly copied
    into the envelope."""
    checks_pass = True
    error_message_list = []

    if workbaskets and envelope:
        workbasket_transaction_pks = [
            transaction.pk for transaction in workbaskets.ordered_transactions()
        ].sort()
        #  I sorted it all as it may give an error if they're just in the wrong order.
        workbasket_transaction_partitions = [
            transaction.partition for transaction in workbaskets.ordered_transactions()
        ].sort()
        workbasket_transaction_count = workbaskets.ordered_transactions().count()
        envelope_transaction_pks = [
            transaction.pk for transaction in envelope.transactions
        ].sort()
        envelope_transaction_partitions = [
            transaction.partition for transaction in envelope.transactions
        ].sort()
        envelope_transaction_count = len(envelope.transactions)

        if envelope_transaction_count != workbasket_transaction_count:
            checks_pass = False
            error_message_list.append("Envelope does not contain all transactions!")
        elif envelope_transaction_pks != workbasket_transaction_pks:
            checks_pass = False
            error_message_list.append(
                "Envelope transaction pks don't match the workbasket transaction pks!",
            )
        elif envelope_transaction_partitions != workbasket_transaction_partitions:
            checks_pass = False
            error_message_list.append(
                "Envelope transaction partitions don't match the workbasket transaction partitions!",
            )

    return {
        "checks_pass": checks_pass,
        "error_message_list": error_message_list,
    }
