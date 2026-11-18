# Ingestion worker

The Celery app reserves the `ingestion` queue and accepts JSON messages via Redis.
Phase 0 registers no tasks or schedules. See [source policy](../../docs/SOURCE_POLICY.md)
for the approval and verification requirements for future adapters.
