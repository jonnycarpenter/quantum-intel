"""Check what model IDs are being used for extraction."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from config.settings import EarningsConfig, SecConfig

ec = EarningsConfig()
sc = SecConfig()

print(f"Earnings extraction model: {ec.extraction_model}")
print(f"SEC extraction model: {sc.extraction_model}")
print(f"EARNINGS_EXTRACTION_MODEL env: {os.getenv('EARNINGS_EXTRACTION_MODEL', '(not set)')}")
print(f"SEC_EXTRACTION_MODEL env: {os.getenv('SEC_EXTRACTION_MODEL', '(not set)')}")
print(f"CLASSIFICATION_MODEL env: {os.getenv('CLASSIFICATION_MODEL', '(not set)')}")
print(f"INTELLIGENCE_MODEL env: {os.getenv('INTELLIGENCE_MODEL', '(not set)')}")
