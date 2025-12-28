import psycopg2
from decouple import config
import os

DATABASE_URL = "postgresql://postgres.zeuuebdjuhtpacxubcmv:nygpik-hyhryg-5jytQy@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

print(f"Connecting to: {DATABASE_URL.replace('nygpik-hyhryg-5jytQy', '********')}")

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Connection successful!")
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    print("Time:", cur.fetchone())
    cur.close()
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
