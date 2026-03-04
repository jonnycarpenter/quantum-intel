"""
Submit User Feedback Tool
=========================

Enables the Intelligence Agent to submit user feedback, feature requests, 
or bug reports directly via email and BigQuery logging.
"""

import json
import logging
import os
from typing import Optional
from datetime import datetime, timezone

from google.cloud import bigquery

logger = logging.getLogger(__name__)

class SubmitUserFeedbackTool:
    """Tool for submitting user feedback to the admin and BigQuery."""

    def __init__(self):
        self.bq_client = None

    def _ensure_bq_client(self) -> None:
        """Lazy-initialize BigQuery client."""
        if self.bq_client is None:
            project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0436975498")
            self.bq_client = bigquery.Client(project=project_id)

    def _table(self) -> str:
        """Get fully qualified table name for feedback."""
        project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0436975498")
        dataset = os.getenv("BIGQUERY_DATASET", "quantum_ai_hub")
        return f"{project_id}.{dataset}.user_feedback"

    async def execute(
        self,
        feedback_type: str,
        message: str,
        user_context: Optional[str] = None
    ) -> str:
        """
        Submit user feedback.

        Args:
            feedback_type: Category of feedback ('bug', 'feature_request', 'general_feedback')
            message: The actual feedback message from the user
            user_context: Optional context about what the user was doing

        Returns:
            JSON string with success status
        """
        logger.info(f"[TOOL] submit_user_feedback: type='{feedback_type}'")

        try:
            # 1. Log to BigQuery
            self._ensure_bq_client()
            
            # Ensure table exists (basic check/create if needed could go here, 
            # but assuming schema management handles it elsewhere)
            rows_to_insert = [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "feedback_type": feedback_type,
                "message": message,
                "user_context": user_context or "",
                "status": "new"
            }]
            
            errors = self.bq_client.insert_rows_json(self._table(), rows_to_insert)
            if errors:
                logger.error(f"[TOOL] submit_user_feedback BQ insert errors: {errors}")
            
            # 2. Send Email Alert (Using SendGrid if available, fallback to basic logging)
            sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
            target_email = "joncarpenter11@gmail.com"
            
            if sendgrid_api_key:
                try:
                    import sendgrid
                    from sendgrid.helpers.mail import Mail, Email, To, Content
                    
                    sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
                    from_email = Email("noreply@ketzero.com")  # Replace with verified sender
                    to_email = To(target_email)
                    subject = f"Ket Zero App Feedback: [{feedback_type.upper()}]"
                    content = Content(
                        "text/plain", 
                        f"New feedback received from the Assistant.\n\n"
                        f"Type: {feedback_type}\n"
                        f"Message:\n{message}\n\n"
                        f"Context: {user_context or 'None'}"
                    )
                    mail = Mail(from_email, to_email, subject, content)
                    response = sg.client.mail.send.post(request_body=mail.get())
                    logger.info(f"SendGrid response: {response.status_code}")
                except ImportError:
                    logger.warning("SendGrid library not installed (`pip install sendgrid`)")
                except Exception as e:
                    logger.error(f"Failed to send email via SendGrid: {e}")
            else:
                logger.warning("SENDGRID_API_KEY not set. Skipping email dispatch.")

            return json.dumps({
                "status": "success",
                "message": "Feedback successfully logged and routed to the development team."
            })

        except Exception as e:
            logger.error(f"[TOOL] submit_user_feedback error: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to submit feedback: {type(e).__name__}"
            })
