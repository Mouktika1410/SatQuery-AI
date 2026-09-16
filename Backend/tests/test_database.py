"""
Direct database connectivity and PostGIS extension verification script.
Can be executed via pytest or directly with python.
"""

from app.database.session import check_db_connection


def test_database_connectivity():
    """Check whether PostgreSQL and PostGIS are reachable and configured."""
    result = check_db_connection()
    print("\n--- SatQuery Database Connectivity Check ---")
    print(f"Connected:        {result.get('connected')}")
    print(f"PostGIS Active:   {result.get('postgis_installed')}")
    print(f"PostGIS Version:  {result.get('postgis_version')}")
    if result.get("error"):
        print(f"Error Details:    {result.get('error')}")
    print("--------------------------------------------\n")
    return result


if __name__ == "__main__":
    test_database_connectivity()
