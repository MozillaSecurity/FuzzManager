from .settings import *  # noqa
INSTALLED_APPS = tuple(list(INSTALLED_APPS) + ["taskmanager"])  # noqa
TC_ROOT_URL = ""  # must be set for taskmanager tests
