import pytest
from hypothesis import settings, Verbosity

settings.register_profile("ci", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("dev", max_examples=10, verbosity=Verbosity.verbose)
settings.load_profile("ci")
