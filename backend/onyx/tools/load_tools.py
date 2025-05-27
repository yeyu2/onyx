#!/usr/bin/env python
"""Script to load tools and add them to personas."""

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from sqlalchemy.orm import Session

from onyx.db.engine import get_session_with_current_tenant
from onyx.tools.built_in_tools import auto_add_weather_tool_to_search_personas
from onyx.tools.built_in_tools import load_builtin_tools
from onyx.tools.built_in_tools import refresh_built_in_tools_cache


def main() -> None:
    """Load tools and add them to personas."""
    print("Loading tools and adding them to personas...")
    
    # Get a database session
    with get_session_with_current_tenant() as db_session:
        db_session: Session
        
        # Load built-in tools
        print("Loading built-in tools...")
        load_builtin_tools(db_session)
        
        # Refresh the built-in tools cache
        print("Refreshing built-in tools cache...")
        refresh_built_in_tools_cache(db_session)
        
        # Add the weather tool to personas with search tools
        print("Adding weather tool to personas with search tools...")
        auto_add_weather_tool_to_search_personas(db_session)
    
    print("Done!")


if __name__ == "__main__":
    main() 