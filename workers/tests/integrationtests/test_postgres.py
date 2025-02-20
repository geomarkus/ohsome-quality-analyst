import asyncio
import os
import unittest

import asyncpg

from ohsome_quality_analyst.geodatabase import client as pg_client


async def get_connection_context_manager():
    async with pg_client.get_connection() as conn:
        return type(conn)


class TestPostgres(unittest.TestCase):
    def test_connection(self):
        instance_type = asyncio.run(get_connection_context_manager())
        self.assertEqual(instance_type, asyncpg.connection.Connection)

    def test_connection_fails(self):
        """Test connection failure error due to wrong credentials"""
        env_backup = {}
        env_names = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        ]
        # Backup and set env to empty string
        for env_name in env_names:
            try:
                env_backup[env_name] = os.environ.pop(env_name)
            except KeyError:
                pass
            os.environ[env_name] = ""

        # Test connection fail
        with self.assertRaises(OSError):
            asyncio.run(get_connection_context_manager())

        # Restore env to previous state
        for env_name in env_names:
            if env_name in env_backup:
                os.environ[env_name] = env_backup[env_name]
            else:
                os.environ.pop(env_name)


if __name__ == "__main__":
    unittest.main()
