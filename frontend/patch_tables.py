import os
import re

files_to_patch = [
    'procurement/PurchaseOrders.tsx',
    'procurement/PurchaseRequests.tsx',
    'receiving/GoodsReceipts.tsx',
    'Requisitions.tsx',
    'Warehouses.tsx',
    'Transfers.tsx'
]

def patch_table(content):
    # 1. Update wrapper
    content = re.sub(r'<div className="overflow-x-auto">', r'<div className="table-container">', content)
    
    # 2. Update table
    content = re.sub(r'<table className="([^"]*)">', lambda m: f'<table className="{m.group(1)} responsive-table">' if 'responsive-table' not in m.group(1) else m.group(0), content)
    
    # 3. Update thead th
    # We will just replace all <th className="..."> with <th className="table-header"> 
    # But wait, it's easier to just add table-header class.
    def replace_th(m):
        cls = m.group(1)
        if 'table-header' not in cls:
            return f'<th className="table-header {cls}">'
        return m.group(0)
    content = re.sub(r'<th className="([^"]*)">', replace_th, content)
    
    # 4. Update tbody tr (skip isLoading ones)
    def replace_tr(m):
        full = m.group(0)
        if 'table-row' not in full and 'key=' in full:
            return full.replace('className="', 'className="table-row ')
        return full
    content = re.sub(r'<tr[^>]*>', replace_tr, content)
    
    # 5. Update tbody td
    def replace_td(m):
        full = m.group(0)
        # Skip colSpan ones
        if 'colSpan' in full:
            return full
        if 'table-cell' not in full:
            if 'className="' in full:
                full = full.replace('className="', 'className="table-cell ')
            else:
                full = full.replace('<td', '<td className="table-cell"')
            
            # We don't have the column name easily, so we just add a generic data-label or we skip it.
            # Actually, responsive-table requires data-label for mobile view.
            # We'll just add data-label="Detail" as fallback if we can't infer.
            if 'data-label' not in full:
                full = full.replace('<td', '<td data-label="Detail"')
            return full
        return full
    content = re.sub(r'<td[^>]*>', replace_td, content)
    
    return content

for file_path in files_to_patch:
    full_path = os.path.join(r'C:\Users\fivid\Desktop\TrackIT-main\frontend\src\pages', file_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = patch_table(content)
        
        # Heuristics for data-labels:
        # We can extract the TH texts and map them to TD's...
        # But this regex is simpler. Let's try basic regex first.
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Patched {file_path}")

