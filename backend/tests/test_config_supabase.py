import unittest

from config import normalize_supabase_database_url


class TestSupabaseUrlNormalization(unittest.TestCase):
    def test_direct_url_becomes_pooler(self):
        direct = (
            "postgresql://postgres:secret@db.abc123.supabase.co:5432/postgres"
        )
        out = normalize_supabase_database_url(direct)
        self.assertIn("pooler.supabase.com", out)
        self.assertIn("postgres.abc123:", out)
        self.assertIn(":6543/", out)

    def test_pooler_url_unchanged(self):
        pooler = (
            "postgresql://postgres.abc123:secret@"
            "aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"
        )
        self.assertEqual(normalize_supabase_database_url(pooler), pooler)
