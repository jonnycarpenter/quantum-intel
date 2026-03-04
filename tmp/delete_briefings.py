"""Delete existing weekly briefings by ID from BigQuery."""
from google.cloud import bigquery

client = bigquery.Client(project="gen-lang-client-0436975498")
table = "gen-lang-client-0436975498.quantum_ai_hub.weekly_briefings"

ids = [
    ("AI", "929f298b-c305-4f6a-ac6b-2c71b5bcc2c5"),
    ("Quantum", "160bfdcf-b99f-4414-bbe0-7dc7fb8310f4"),
]

for label, bid in ids:
    q = f"DELETE FROM {table} WHERE id = @id"
    job = client.query(q, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("id", "STRING", bid)]
    ))
    job.result()
    print(f"{label} briefing ({bid}): {job.num_dml_affected_rows} row(s) deleted")
