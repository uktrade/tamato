# XXX need to keep this for migrations to work, can delete later
def to_hmrc(instance):
    """Generate the filepath to upload to HMRC."""

    return f"tohmrc/staging/DIT{instance.envelope.envelope_id}.xml"
