import sys, os, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from models.article import RawArticle
from processing.classifier import ContentClassifier
from datetime import datetime, timezone

async def run_test():
    article = RawArticle(
        url="https://example.com/quantum-news",
        title="IBM Announces 10k Qubit System with Commercial Cloud Deployment",
        source_name="Quantum Tech News",
        source_url="https://example.com",
        published_at=datetime.now(timezone.utc),
        summary="IBM today announced a major breakthrough in quantum computing, revealing a 10,000-qubit processor. This new system, named Condor V2, will be deployed on IBM Cloud starting next month. Wall Street analysts expect this to disrupt the logistics and financial modeling sectors immediately. Several major banks have already signed on as early access partners, signaling strong enterprise demand and a major shift in the quantum computing market."
    )
    
    classifier = ContentClassifier(domain="quantum")
    print("Classifying test article...")
    result = await classifier.classify(article)
    
    if result:
        print("\n--- Classification Result ---")
        print(f"Category: {result.primary_category}")
        print(f"Priority: {result.priority.value}")
        print(f"Relevance: {result.relevance_score}")
        print(f"Summary: {result.summary}")
        print(f"Time to Market: {result.time_to_market_impact}")
        print(f"Disrupted Industries: {result.disrupted_industries}")
        print(f"Investment Signal: {result.investment_signal}")
        print(f"Confidence: {result.confidence}")
        
        # Test DB saving
        from storage.sqlite import SQLiteStorage
        storage = SQLiteStorage()
        # Convert to ClassifiedArticle so we can save it
        from storage.base import ClassifiedArticle
        
        # In this project, ClassificationResult merges with RawArticle to make ClassifiedArticle, but in sqlite.py save_articles it expects ClassifiedArticle. Let's see how run_ingestion creates it.
        # Actually wait, let's just use the orchestrator approach or mock the ClassifiedArticle.
        raw_dict = article.__dict__.copy()
        raw_dict.update(result.__dict__)
        
        ca = ClassifiedArticle.from_dict(raw_dict)
        
        saved = await storage.save_articles([ca])
        print(f"\nSaved {saved} article to DB.")
        await storage.close()
    else:
        print("Failed to classify.")

if __name__ == "__main__":
    asyncio.run(run_test())
