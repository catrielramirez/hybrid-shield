import sys
sys.stdout.reconfigure(line_buffering=True)
from google.cloud import logging as cloud_logging
from collections import Counter

client = cloud_logging.Client(project='ecommerce-police-portfolio')

# Broad filter for anything from cloud_function, cloud_run_revision, or reasoning engine
filter_str = '''
(resource.type="cloud_function" OR resource.type="cloud_run_revision" OR resource.type="aiplatform.googleapis.com/ReasoningEngine")
AND timestamp >= "2026-06-05T00:00:00Z"
AND timestamp <= "2026-06-08T23:59:59Z"
'''

print(f"Querying app logs...\\n")
try:
    entries = client.list_entries(filter_=filter_str, page_size=100)
    
    count = 0
    resources = Counter()
    
    for entry in entries:
        count += 1
        res_type = entry.resource.type if entry.resource else 'unknown'
        resources[res_type] += 1
        
        if count <= 5:
            text = entry.payload if isinstance(entry.payload, str) else str(entry.payload)[:200]
            print(f"[{entry.timestamp}] {res_type}: {text}")
            
        if count >= 100:
            break

    print(f"\\n--- Analysis (Sampled {count} logs) ---")
    print(f"Resources: {dict(resources)}")

except Exception as e:
    print(f"Error querying logs: {e}")
