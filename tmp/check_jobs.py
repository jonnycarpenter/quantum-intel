"""Check Cloud Run Job execution history."""
import os
import subprocess

# Check last executions of podcast jobs
jobs = ['quantum-podcasts', 'ai-podcasts']
region = 'us-central1'
project = 'gen-lang-client-0436975498'

for job in jobs:
    print(f"\n=== {job} ===")
    result = subprocess.run(
        ['gcloud', 'run', 'jobs', 'executions', 'list',
         f'--job={job}', f'--region={region}', f'--project={project}',
         '--limit=3', '--format=table(name,status.conditions[0].type,status.conditions[0].status,createTime)'],
        capture_output=True, text=True
    )
    print(result.stdout or result.stderr)
