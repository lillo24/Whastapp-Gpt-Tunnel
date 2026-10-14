# Synthetic fixtures

`schema.sql` is a proposed WA01/WA02 contract, not a migration or production
initializer. Generate invented data without installing upstream packages:

```powershell
python .\scripts\generate_synthetic_fixture.py --output-dir .local-fixtures\example
```

Use an absolute Python >=3.11 executable path if `python` is a Windows Store alias.
Output is restricted to a fresh subdirectory of `.local-fixtures/`; existing
paths are refused. Generated SQLite, JSON events and manifest are Git-ignored.
Do not replace them with exports or real message captures.

The fixture has 4 chats, 12 unique messages and 13 incoming records, including
one duplicate replay. It includes direct/group/own history, duplicate IDs across
chats, timestamp ties, leap-day and UTC-offset boundaries, Unicode/multiline
text, two contacts with the same display name, unresolved sender mapping, a
long prompt-injection string and SQL-looking text. A media message contains only
an `image` marker, no bytes, local filename, URL or key.

Every identifier begins with `fixture-`; names/content are invented. Status is
explicitly synthetic, unlinked and disconnected, with partial-history warning.
This tests storage assumptions; it does not simulate a working WhatsApp session
or certify LLM prompt-injection resistance. WA01 must add actual synthetic
protobuf/event ingest tests for edits/deletes/reactions and unsupported wrappers.
