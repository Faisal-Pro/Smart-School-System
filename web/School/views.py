"""Compatibility layer: urls.py keeps using views.<name>.
The real code lives in views_*.py (one file per area)."""
from .views_public import *  # noqa: F401,F403
from .views_admin import *  # noqa: F401,F403
from .views_teacher import *  # noqa: F401,F403
from .views_materials import *  # noqa: F401,F403
from .views_announcements import *  # noqa: F401,F403
from .views_student import *  # noqa: F401,F403
from .views_quiz import *  # noqa: F401,F403
