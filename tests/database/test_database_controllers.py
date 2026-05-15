"""Database controllers integration tests.

Note: GuildController and GuildConfigController have been removed.
Only controllers for remaining models (Case, Snippet, PermissionRank, etc.) are tested.
"""

import pytest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
