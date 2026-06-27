import os

paths = ['backend/app', 'backend/tests', 'backend/db_seed.py']
files_to_update = []

for p in paths:
    if os.path.isfile(p):
        files_to_update.append(p)
    else:
        for root, _, files in os.walk(p):
            for f in files:
                if f.endswith('.py'):
                    files_to_update.append(os.path.join(root, f))

for f in files_to_update:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        new_content = content.replace('"staff"', '"logistics_officer"').replace("'staff'", "'logistics_officer'")
        new_content = new_content.replace('"dept_head"', '"procurement_officer"').replace("'dept_head'", "'procurement_officer'")
        new_content = new_content.replace('"viewer"', '"employee"').replace("'viewer'", "'employee'")
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f'Updated {f}')
    except Exception as e:
        print(f"Error reading {f}: {e}")
