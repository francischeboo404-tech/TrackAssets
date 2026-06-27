import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host="aws-0-eu-west-1.pooler.supabase.com",
        port=6543,
        user="postgres.zatfehhphmxhtznnmggn",
        password="Fr%4038998653",
        dbname="postgres",
        sslmode="require"
    )
    print("Successfully connected via psycopg2!")
    conn.close()
except Exception as e:
    print("psycopg2 error:", e)
