import sys
sys.stdout.reconfigure(line_buffering=True)
import os
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import query

client = monitoring_v3.MetricServiceClient()
project_id = 'ecommerce-police-portfolio'
project_name = f"projects/{project_id}"

# Query Vertex AI prediction request count
q = query.Query(
    client,
    project_name,
    'aiplatform.googleapis.com/prediction/online/predict_requests',
    minutes=60*24*5, # Last 5 days
)

print("Querying Vertex AI prediction metrics...")
try:
    for time_series in q:
        model = time_series.resource.labels.get('model_id', 'unknown')
        for point in time_series.points:
            print(f"Time: {point.interval.end_time} | Model: {model} | Count: {point.value.int64_value}")
except Exception as e:
    print(f"Error querying metrics: {e}")
