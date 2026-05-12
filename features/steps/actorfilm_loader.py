# Behave 1.2.6 only flat-scans features/steps/*.py.
# This shim imports subdirectory step modules so their decorators register.
import database.postgres.actorfilm_steps  # noqa: F401