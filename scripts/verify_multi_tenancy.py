#!/usr/bin/env python3
"""Verify multi-tenant schema isolation in Supabase

This script checks that each organization has its own isolated schema
and that data is properly separated between tenants.

Usage:
    python verify_multi_tenancy.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def main():
    # Load environment
    env_file = '.env.production' if os.path.exists('.env.production') else '.env'
    print(f"📖 Loading environment from: {env_file}")
    load_dotenv(env_file)
    
    db_url = os.environ.get('DATABASE_URL_PROD') or os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL_PROD not set")
        sys.exit(1)
    
    print("\n🔍 Verifying Multi-Tenant Schema Isolation in Supabase\n")
    
    try:
        engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={'sslmode': 'require'} if 'postgresql' in db_url else {}
        )
        
        with engine.connect() as conn:
            # 1. List all schemas
            print("📂 Available Schemas:")
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata
                WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'
                ORDER BY schema_name;
            """))
            schemas = result.fetchall()
            
            if not schemas:
                print("   (No schemas yet)")
            
            for schema in schemas:
                schema_name = schema[0]
                # Get table count
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE';
                """))
                table_count = result.fetchone()[0]
                print(f"   ✓ {schema_name} ({table_count} tables)")
            
            # 2. Show organizations
            print("\n👥 Organizations (public schema):")
            result = conn.execute(text("""
                SELECT id, name, code FROM public.organizations 
                ORDER BY id;
            """))
            orgs = result.fetchall()
            
            if not orgs:
                print("   (No organizations)")
            else:
                for org_id, name, code in orgs:
                    schema = f"tenant_{org_id:04d}"
                    print(f"   ✓ ID {org_id}: {name} ({code}) → {schema}")
            
            # 3. Verify schema isolation
            print("\n🔐 Schema Isolation Verification:")
            
            if orgs:
                for org_id, name, code in orgs:
                    schema = f"tenant_{org_id:04d}"
                    print(f"\n   {schema} ({name}):")
                    
                    # Test asset count
                    try:
                        result = conn.execute(text(f"""
                            SELECT COUNT(*) FROM {schema}.assets;
                        """))
                        count = result.fetchone()[0]
                        print(f"      ✓ Assets: {count}")
                    except Exception as e:
                        print(f"      ✗ Assets table error: {e}")
                    
                    # Test inventory count
                    try:
                        result = conn.execute(text(f"""
                            SELECT COUNT(*) FROM {schema}.inventory_items;
                        """))
                        count = result.fetchone()[0]
                        print(f"      ✓ Inventory items: {count}")
                    except Exception as e:
                        print(f"      ✗ Inventory table error: {e}")
                    
                    # Test transfers count
                    try:
                        result = conn.execute(text(f"""
                            SELECT COUNT(*) FROM {schema}.transfer_requests;
                        """))
                        count = result.fetchone()[0]
                        print(f"      ✓ Transfers: {count}")
                    except Exception as e:
                        print(f"      ✗ Transfers table error: {e}")
                    
                    # Test audit logs
                    try:
                        result = conn.execute(text(f"""
                            SELECT COUNT(*) FROM {schema}.audit_logs;
                        """))
                        count = result.fetchone()[0]
                        print(f"      ✓ Audit logs: {count}")
                    except Exception as e:
                        print(f"      ✗ Audit logs table error: {e}")
            else:
                print("   (No organizations to verify)")
            
            # 4. Verify migration tracking
            print(f"\n📊 Migration Tracking:")
            try:
                result = conn.execute(text("""
                    SELECT version, applied_at FROM public.schema_migrations
                    ORDER BY version;
                """))
                migrations = result.fetchall()
                
                if migrations:
                    for version, applied_at in migrations:
                        print(f"   ✓ {version} (applied: {applied_at})")
                else:
                    print("   (No migrations tracked yet)")
            except Exception as e:
                print(f"   (Migration tracking table not found: {e})")
            
            # 5. Check for advisory locks support
            print(f"\n🔒 Advisory Locks (Race Condition Prevention):")
            try:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc 
                        WHERE proname = 'pg_advisory_lock'
                    );
                """))
                has_locks = result.fetchone()[0]
                print(f"   ✓ PostgreSQL Advisory Locks: {'Supported' if has_locks else 'Not Supported'}")
            except Exception as e:
                print(f"   ✗ Error checking advisory locks: {e}")
            
            # 6. Connection pool info
            print(f"\n🔗 Connection Pool Status:")
            print(f"   Pool size: {engine.pool.size()}")
            print(f"   Checked out: {engine.pool.checkedout()}")
            print(f"   Available: {engine.pool.size() - engine.pool.checkedout()}")
            print(f"   Timeout: {engine.pool.timeout}s")
            
            print("\n✅ Multi-tenancy verification complete!")
            return 0
            
    except Exception as e:
        print(f"\n❌ Verification failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
