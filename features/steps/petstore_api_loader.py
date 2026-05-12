# Behave 1.2.6 only flat-scans features/steps/*.py (no recursion).
# This shim imports each domain step module so their @given/@when/@then
# decorators fire and register with behave's global step registry.
# PathManager adds features/steps/ to sys.path before this file is exec'd,
# so "api.rest.*" resolves correctly.
import api.rest.pet_steps       # noqa: F401
import api.rest.store_steps     # noqa: F401
import api.rest.user_steps      # noqa: F401
import api.rest.contract_steps  # noqa: F401