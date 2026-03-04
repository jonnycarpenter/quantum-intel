"""Check Cloud Run Job execution history using Python client."""
import os
from dotenv import load_dotenv
load_dotenv()

try:
    from google.cloud import run_v2
    
    project = os.environ.get('GCP_PROJECT_ID', 'gen-lang-client-0436975498')
    region = 'us-central1'
    
    client = run_v2.ExecutionsClient()
    
    jobs = ['quantum-podcasts', 'ai-podcasts']
    for job in jobs:
        print(f"\n=== {job} ===")
        parent = f"projects/{project}/locations/{region}/jobs/{job}"
        try:
            request = run_v2.ListExecutionsRequest(parent=parent)
            page_result = client.list_executions(request=request)
            count = 0
            for execution in page_result:
                if count >= 3:
                    break
                conditions = execution.conditions
                status = "UNKNOWN"
                for c in conditions:
                    if c.type_ == "Completed":
                        status = "Succeeded" if c.state.name == "CONDITION_SUCCEEDED" else f"Failed ({c.state.name})"
                        break
                print(f"  {execution.create_time.strftime('%Y-%m-%d %H:%M')} | Status: {status}")
                count += 1
            if count == 0:
                print("  No executions found")
        except Exception as e:
            print(f"  ERROR: {e}")
except ImportError:
    print("google-cloud-run not installed, trying REST API approach")
    from google.cloud import bigquery
    # Fallback: just check if the podcast pipeline would work by doing a dry check
    print("Skipping job execution check - gcloud auth needed")
