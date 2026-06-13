#!/usr/bin/env python3
"""Test Supabase PostgreSQL connection

This script verifies that the connection to Supabase is working correctly
and displays database information.

Usage:
    python test_supabase_connection.py
    
Environment variables required:
    DATABASE_URL_PROD: PostgreSQL connection string
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def main():
    # Try loading from .env.production first, then .env
    env_file = '.env.production' if os.path.exists('.env.production') else '.env'
    print(f"📖 Loading environment from: {env_file}")
    load_dotenv(env_file)
    
    # Get connection string
    db_url = os.environ.get('DATABASE_URL_PROD')
    if not db_url:
        db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("❌ ERROR: DATABASE_URL_PROD or DATABASE_URL not set in environment")
        print("\n   Set it with:")
        print("   export DATABASE_URL_PROD='postgresql://...'")
        sys.exit(1)
    
    # Parse connection info for display (hide password)
    if '@' in db_url:
        host_port = db_url.split('@')[1].split('?')[0]
        display_url = f"postgresql://<user>:<pass>@{host_port}"
    else:
        display_url = db_url
    
    print(f"\n📍 Connecting to: {display_url}")
    print("⏳ Testing connection...")
    
    try:
        # Create engine with SSL required
        engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={'sslmode': 'require'} if 'postgresql' in db_url else {}
        )
        
        # Test connection
        with engine.connect() as conn:
            # Get PostgreSQL version
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"\n✅ Connected successfully!")
            print(f"📦 PostgreSQL Version: {version}")
            
            # Get current database
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"📂 Current Database: {db_name}")
            
            # Get current user
            result = conn.execute(text("SELECT current_user;"))
            user = result.fetchone()[0]
            print(f"👤 Current User: {user}")
            
            # Test schema listing
            print(f"\n📂 Available Schemas:")
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'extensions')
                ORDER BY schema_name;
            """))
            schemas = result.fetchall()
            
            if schemas:
                for schema in schemas:
                    schema_name = schema[0]
                    # Count tables in schema
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE';
                    """))
                    table_count = result.fetchone()[0]
                    print(f"   ✓ {schema_name} ({table_count} tables)")
            else:
                print("   ✓ public (default)")
            
            # Check for multi-tenant schemas
            print(f"\n🔐 Multi-Tenant Schemas (tenant_*):")
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata
                WHERE schema_name LIKE 'tenant_%'
                ORDER BY schema_name;
            """))
            tenant_schemas = result.fetchall()
            
            if tenant_schemas:
                for schema in tenant_schemas:
                    schema_name = schema[0]
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE';
                    """))
                    table_count = result.fetchone()[0]
                    print(f"   ✓ {schema_name} ({table_count} tables)")
            else:
                print("   (None yet - will be created during organization registration)")
            
            # Check for organizations
            print(f"\n👥 Organizations:")
            try:
                result = conn.execute(text("""
                    SELECT id, name, code FROM public.organizations 
                    ORDER BY id;
                """))
                orgs = result.fetchall()
                
                if orgs:
                    for org_id, name, code in orgs:
                        schema_name = f"tenant_{org_id:04d}"
                        print(f"   ✓ ID {org_id}: {name} ({code})")
                        print(f"      └─ Schema: {schema_name}")
                else:
                    print("   (No organizations yet - register via /api/auth/register)")
            except Exception as e:
                print(f"   (Organizations table not yet created: {e})")
            
            # Connection pool info
            print(f"\n🔗 Connection Pool Status:")
            print(f"   Pool size: {engine.pool.size()}")
            print(f"   Checked out: {engine.pool.checkedout()}")
            print(f"   Overflow: {engine.pool.overflow()}")
            print(f"   Timeout: {engine.pool.timeout}")
        
        print("\n✅ Supabase connection verified successfully!")
        print("\n📝 Next steps:")
        print("   1. Start the Flask app: python run.py")
        print("   2. Register an organization: curl -X POST http://localhost:5000/api/auth/register ...")
        print("   3. Verify schema creation: python verify_multi_tenancy.py")
        return 0
        
    except Exception as e:
        print(f"\n❌ Connection failed: {type(e).__name__}: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check DATABASE_URL_PROD environment variable is set")
        print("   2. Verify password is correct: Fr@38998653")
        print("   3. Verify Supabase project is running (not paused)")
        print("   4. Check firewall allows connection to Supabase")
        print("   5. Verify sslmode=require is in connection string")
        return 1

if __name__ == '__main__':
    sys.exit(main())
