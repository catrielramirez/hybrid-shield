import sys
sys.stdout.reconfigure(line_buffering=True)
from google.cloud import logging as cloud_logging

client = cloud_logging.Client(project='ecommerce-police-portfolio')

filter_str = '''
(resource.type="cloud_function" OR resource.type="cloud_run_revision" OR resource.type="aiplatform.googleapis.com/ReasoningEngine")
AND timestamp >= "2026-06-05T00:00:00Z"
AND timestamp <= "2026-06-08T23:59:59Z"
AND (textPayload:"Iniciando procesamiento" OR textPayload:"Grafo ejecutado" OR jsonPayload.message:"Iniciando procesamiento" OR jsonPayload.message:"Grafo ejecutado" OR textPayload:"Enviando payload" OR jsonPayload.message:"Enviando payload")
'''

print(f"Querying app logs for function execution...\\n")
try:
    entries = client.list_entries(filter_=filter_str, page_size=100)
    count = 0
    for entry in entries:
        count += 1
        msg = entry.payload if isinstance(entry.payload, str) else entry.payload.get('message', str(entry.payload))
        print(f"[{entry.timestamp}] {msg}")
        if count >= 20: break
    print(f"\\nFound {count} specific trigger logs.")
except Exception as e:
    print(f"Error querying logs: {e}")
