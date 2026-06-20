import sys
sys.stdout.reconfigure(line_buffering=True)
from google.cloud import logging as cloud_logging
from collections import Counter

client = cloud_logging.Client(project='ecommerce-police-portfolio')

filter_str = '''
logName="projects/ecommerce-police-portfolio/logs/cloudaudit.googleapis.com%2Fdata_access"
AND protoPayload.serviceName="aiplatform.googleapis.com"
AND timestamp >= "2026-06-05T00:00:00Z"
AND timestamp <= "2026-06-08T23:59:59Z"
'''

print(f"Querying audit logs...\\n")
try:
    entries = client.list_entries(filter_=filter_str, page_size=100)
    
    count = 0
    principals = Counter()
    methods = Counter()
    ips = Counter()

    for entry in entries:
        count += 1
        payload = entry.payload or {}
        
        auth = payload.get('authenticationInfo', {})
        req_meta = payload.get('requestMetadata', {})
        
        principal = auth.get('principalEmail', 'unknown')
        method = payload.get('methodName', 'unknown')
        ip = req_meta.get('callerIp', 'unknown')
        
        principals[principal] += 1
        methods[method] += 1
        ips[ip] += 1
        
        if count <= 5:
            print(f"[{entry.timestamp}] Method: {method} | Caller: {principal} | IP: {ip}")
            
        if count >= 100:
            break

    print(f"\\n--- Analysis (Sampled {count} logs) ---")
    print(f"Principals: {dict(principals)}")
    print(f"IPs: {dict(ips)}")
    print(f"Methods: {dict(methods)}")

except Exception as e:
    print(f"Error querying logs: {e}")
