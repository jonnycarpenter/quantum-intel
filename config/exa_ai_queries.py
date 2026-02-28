"""
Exa Search Queries — AI Use Case Intelligence
===============================================

198 use-case oriented queries for discovering AI implementations with proven ROI.
100 industry-focused queries (20 industries x 5) + 98 department-focused queries (14 departments x 7).
"""

from typing import List, Dict, Any


AI_EXA_QUERIES: List[Dict[str, Any]] = [
    # =========================================================================
    # INDUSTRY QUERIES (100 queries, 20 industries x 5 each)
    # =========================================================================

    # Industry: Retail (5 queries)
    {"query": "AI implementation retail customer experience ROI case study 2025", "theme": "industry_retail", "id": 1},
    {"query": "machine learning retail demand forecasting results revenue", "theme": "industry_retail", "id": 2},
    {"query": "AI personalization retail conversion rate improvement metrics", "theme": "industry_retail", "id": 3},
    {"query": "computer vision retail inventory management cost savings", "theme": "industry_retail", "id": 4},
    {"query": "generative AI retail product recommendation deployment results", "theme": "industry_retail", "id": 5},

    # Industry: Manufacturing (5 queries)
    {"query": "AI predictive maintenance manufacturing downtime reduction ROI", "theme": "industry_manufacturing", "id": 6},
    {"query": "machine learning quality control manufacturing defect detection results", "theme": "industry_manufacturing", "id": 7},
    {"query": "AI digital twin manufacturing production optimization case study", "theme": "industry_manufacturing", "id": 8},
    {"query": "computer vision manufacturing inspection automation deployment", "theme": "industry_manufacturing", "id": 9},
    {"query": "AI supply chain manufacturing yield improvement metrics", "theme": "industry_manufacturing", "id": 10},

    # Industry: Supply Chain (5 queries)
    {"query": "AI supply chain optimization logistics cost reduction case study", "theme": "industry_supply_chain", "id": 11},
    {"query": "machine learning demand planning supply chain accuracy improvement", "theme": "industry_supply_chain", "id": 12},
    {"query": "AI warehouse automation efficiency metrics deployment", "theme": "industry_supply_chain", "id": 13},
    {"query": "predictive analytics supply chain disruption prevention ROI", "theme": "industry_supply_chain", "id": 14},
    {"query": "AI route optimization delivery fleet management savings", "theme": "industry_supply_chain", "id": 15},

    # Industry: Construction (5 queries)
    {"query": "AI construction project management scheduling optimization results", "theme": "industry_construction", "id": 16},
    {"query": "computer vision construction site safety monitoring deployment", "theme": "industry_construction", "id": 17},
    {"query": "AI construction cost estimation accuracy improvement case study", "theme": "industry_construction", "id": 18},
    {"query": "machine learning construction quality inspection defect detection", "theme": "industry_construction", "id": 19},
    {"query": "generative AI building design optimization sustainability metrics", "theme": "industry_construction", "id": 20},

    # Industry: Healthcare (5 queries)
    {"query": "AI healthcare diagnostics accuracy improvement patient outcomes", "theme": "industry_healthcare", "id": 21},
    {"query": "machine learning clinical trial optimization time savings results", "theme": "industry_healthcare", "id": 22},
    {"query": "AI hospital operations scheduling efficiency cost reduction", "theme": "industry_healthcare", "id": 23},
    {"query": "AI medical imaging radiology deployment accuracy metrics", "theme": "industry_healthcare", "id": 24},
    {"query": "NLP healthcare electronic health records automation case study", "theme": "industry_healthcare", "id": 25},

    # Industry: Pharma (5 queries)
    {"query": "AI drug discovery pharmaceutical pipeline acceleration results", "theme": "industry_pharma", "id": 26},
    {"query": "machine learning pharma clinical trial patient recruitment improvement", "theme": "industry_pharma", "id": 27},
    {"query": "AI pharmaceutical manufacturing quality control deployment", "theme": "industry_pharma", "id": 28},
    {"query": "generative AI molecule design drug development case study", "theme": "industry_pharma", "id": 29},
    {"query": "AI pharmacovigilance adverse event detection automation ROI", "theme": "industry_pharma", "id": 30},

    # Industry: Financial Services (5 queries)
    {"query": "AI fraud detection banking financial services results metrics", "theme": "industry_financial_services", "id": 31},
    {"query": "machine learning credit scoring risk assessment accuracy improvement", "theme": "industry_financial_services", "id": 32},
    {"query": "AI trading algorithmic portfolio management returns case study", "theme": "industry_financial_services", "id": 33},
    {"query": "LLM financial services customer service automation cost savings", "theme": "industry_financial_services", "id": 34},
    {"query": "AI regulatory compliance AML KYC automation deployment results", "theme": "industry_financial_services", "id": 35},

    # Industry: Insurance (5 queries)
    {"query": "AI insurance claims processing automation cost reduction case study", "theme": "industry_insurance", "id": 36},
    {"query": "machine learning insurance underwriting risk pricing accuracy", "theme": "industry_insurance", "id": 37},
    {"query": "AI insurance fraud detection savings deployment results", "theme": "industry_insurance", "id": 38},
    {"query": "NLP insurance document processing automation efficiency metrics", "theme": "industry_insurance", "id": 39},
    {"query": "AI actuarial modeling insurance loss prediction improvement", "theme": "industry_insurance", "id": 40},

    # Industry: Energy (5 queries)
    {"query": "AI energy grid optimization renewable integration efficiency results", "theme": "industry_energy", "id": 41},
    {"query": "machine learning oil gas production optimization cost savings", "theme": "industry_energy", "id": 42},
    {"query": "AI predictive maintenance energy infrastructure deployment ROI", "theme": "industry_energy", "id": 43},
    {"query": "AI energy trading demand forecasting accuracy improvement", "theme": "industry_energy", "id": 44},
    {"query": "computer vision solar wind farm inspection automation case study", "theme": "industry_energy", "id": 45},

    # Industry: Telecom (5 queries)
    {"query": "AI telecom network optimization performance improvement deployment", "theme": "industry_telecom", "id": 46},
    {"query": "machine learning telecom churn prediction retention results", "theme": "industry_telecom", "id": 47},
    {"query": "AI customer service telecom chatbot resolution rate metrics", "theme": "industry_telecom", "id": 48},
    {"query": "AI telecom 5G network management automation case study", "theme": "industry_telecom", "id": 49},
    {"query": "predictive analytics telecom infrastructure maintenance savings", "theme": "industry_telecom", "id": 50},

    # Industry: Transportation (5 queries)
    {"query": "AI autonomous vehicle fleet management deployment results", "theme": "industry_transportation", "id": 51},
    {"query": "machine learning transportation route optimization fuel savings", "theme": "industry_transportation", "id": 52},
    {"query": "AI traffic management smart city congestion reduction metrics", "theme": "industry_transportation", "id": 53},
    {"query": "AI logistics last-mile delivery optimization cost reduction", "theme": "industry_transportation", "id": 54},
    {"query": "predictive maintenance aviation airline safety efficiency ROI", "theme": "industry_transportation", "id": 55},

    # Industry: Agriculture (5 queries)
    {"query": "AI precision agriculture crop yield improvement metrics deployment", "theme": "industry_agriculture", "id": 56},
    {"query": "computer vision agriculture pest detection plant disease results", "theme": "industry_agriculture", "id": 57},
    {"query": "machine learning irrigation optimization water savings case study", "theme": "industry_agriculture", "id": 58},
    {"query": "AI livestock monitoring health prediction farming ROI", "theme": "industry_agriculture", "id": 59},
    {"query": "drone AI agriculture field mapping soil analysis deployment", "theme": "industry_agriculture", "id": 60},

    # Industry: Real Estate (5 queries)
    {"query": "AI real estate property valuation accuracy improvement results", "theme": "industry_real_estate", "id": 61},
    {"query": "machine learning real estate market prediction investment returns", "theme": "industry_real_estate", "id": 62},
    {"query": "AI property management tenant screening automation efficiency", "theme": "industry_real_estate", "id": 63},
    {"query": "computer vision real estate virtual staging inspection deployment", "theme": "industry_real_estate", "id": 64},
    {"query": "generative AI real estate listing optimization conversion case study", "theme": "industry_real_estate", "id": 65},

    # Industry: Hospitality (5 queries)
    {"query": "AI hotel revenue management dynamic pricing optimization results", "theme": "industry_hospitality", "id": 66},
    {"query": "machine learning restaurant demand forecasting waste reduction", "theme": "industry_hospitality", "id": 67},
    {"query": "AI hospitality customer personalization satisfaction improvement", "theme": "industry_hospitality", "id": 68},
    {"query": "chatbot AI hotel guest services automation cost savings", "theme": "industry_hospitality", "id": 69},
    {"query": "AI hospitality workforce scheduling labor optimization deployment", "theme": "industry_hospitality", "id": 70},

    # Industry: Media (5 queries)
    {"query": "generative AI media content creation production cost reduction", "theme": "industry_media", "id": 71},
    {"query": "AI recommendation engine media streaming engagement metrics", "theme": "industry_media", "id": 72},
    {"query": "AI advertising targeting media campaign ROI improvement results", "theme": "industry_media", "id": 73},
    {"query": "NLP AI content moderation social media automation deployment", "theme": "industry_media", "id": 74},
    {"query": "AI newsroom automation journalism fact-checking case study", "theme": "industry_media", "id": 75},

    # Industry: Professional Services (5 queries)
    {"query": "AI legal document review contract analysis time savings results", "theme": "industry_professional_services", "id": 76},
    {"query": "LLM consulting firm knowledge management productivity improvement", "theme": "industry_professional_services", "id": 77},
    {"query": "AI accounting audit automation accuracy efficiency deployment", "theme": "industry_professional_services", "id": 78},
    {"query": "AI tax preparation professional services cost reduction case study", "theme": "industry_professional_services", "id": 79},
    {"query": "generative AI professional services proposal generation automation", "theme": "industry_professional_services", "id": 80},

    # Industry: CPG (5 queries)
    {"query": "AI consumer packaged goods demand forecasting accuracy results", "theme": "industry_cpg", "id": 81},
    {"query": "machine learning CPG new product development optimization ROI", "theme": "industry_cpg", "id": 82},
    {"query": "AI CPG pricing optimization revenue improvement deployment", "theme": "industry_cpg", "id": 83},
    {"query": "computer vision CPG shelf analytics retail execution case study", "theme": "industry_cpg", "id": 84},
    {"query": "AI consumer insights CPG market research automation savings", "theme": "industry_cpg", "id": 85},

    # Industry: Aerospace (5 queries)
    {"query": "AI aerospace predictive maintenance aircraft safety savings", "theme": "industry_aerospace", "id": 86},
    {"query": "machine learning aerospace design optimization simulation results", "theme": "industry_aerospace", "id": 87},
    {"query": "AI satellite imagery analysis aerospace defense deployment", "theme": "industry_aerospace", "id": 88},
    {"query": "AI aerospace supply chain quality control inspection metrics", "theme": "industry_aerospace", "id": 89},
    {"query": "digital twin AI aerospace engine monitoring case study", "theme": "industry_aerospace", "id": 90},

    # Industry: Automotive (5 queries)
    {"query": "AI autonomous driving vehicle development deployment results", "theme": "industry_automotive", "id": 91},
    {"query": "machine learning automotive manufacturing quality inspection ROI", "theme": "industry_automotive", "id": 92},
    {"query": "AI automotive design generative engineering optimization", "theme": "industry_automotive", "id": 93},
    {"query": "AI connected car data analytics customer experience metrics", "theme": "industry_automotive", "id": 94},
    {"query": "predictive maintenance AI automotive fleet management savings", "theme": "industry_automotive", "id": 95},

    # Industry: Food & Beverage (5 queries)
    {"query": "AI food beverage quality control production optimization results", "theme": "industry_food_beverage", "id": 96},
    {"query": "machine learning food safety monitoring contamination detection", "theme": "industry_food_beverage", "id": 97},
    {"query": "AI food beverage supply chain demand forecasting waste reduction", "theme": "industry_food_beverage", "id": 98},
    {"query": "AI restaurant menu optimization pricing revenue case study", "theme": "industry_food_beverage", "id": 99},
    {"query": "computer vision food processing inspection automation deployment", "theme": "industry_food_beverage", "id": 100},

    # =========================================================================
    # DEPARTMENT QUERIES (98 queries, 14 departments x 7 each)
    # =========================================================================

    # Department: Marketing (7 queries)
    {"query": "AI marketing campaign optimization conversion rate improvement ROI", "theme": "department_marketing", "id": 101},
    {"query": "generative AI content marketing creation automation productivity", "theme": "department_marketing", "id": 102},
    {"query": "AI customer segmentation personalization marketing results", "theme": "department_marketing", "id": 103},
    {"query": "machine learning marketing attribution modeling accuracy metrics", "theme": "department_marketing", "id": 104},
    {"query": "AI SEO content optimization organic traffic growth case study", "theme": "department_marketing", "id": 105},
    {"query": "AI email marketing automation engagement rate improvement", "theme": "department_marketing", "id": 106},
    {"query": "predictive analytics marketing customer lifetime value results", "theme": "department_marketing", "id": 107},

    # Department: Finance (7 queries)
    {"query": "AI finance department automation accounts payable savings", "theme": "department_finance", "id": 108},
    {"query": "machine learning financial forecasting planning accuracy improvement", "theme": "department_finance", "id": 109},
    {"query": "AI expense management fraud detection corporate finance results", "theme": "department_finance", "id": 110},
    {"query": "AI invoice processing automation finance department cost reduction", "theme": "department_finance", "id": 111},
    {"query": "LLM financial analysis reporting automation productivity metrics", "theme": "department_finance", "id": 112},
    {"query": "AI cash flow forecasting working capital optimization case study", "theme": "department_finance", "id": 113},
    {"query": "AI audit trail compliance automation financial controls deployment", "theme": "department_finance", "id": 114},

    # Department: Sales (7 queries)
    {"query": "AI sales forecasting pipeline prediction accuracy improvement", "theme": "department_sales", "id": 115},
    {"query": "AI lead scoring prioritization sales conversion rate results", "theme": "department_sales", "id": 116},
    {"query": "generative AI sales outreach email personalization metrics", "theme": "department_sales", "id": 117},
    {"query": "AI CRM enrichment sales intelligence automation deployment", "theme": "department_sales", "id": 118},
    {"query": "AI conversation intelligence sales coaching win rate case study", "theme": "department_sales", "id": 119},
    {"query": "machine learning deal scoring sales cycle acceleration ROI", "theme": "department_sales", "id": 120},
    {"query": "AI pricing optimization sales revenue improvement results", "theme": "department_sales", "id": 121},

    # Department: Operations (7 queries)
    {"query": "AI operations process automation efficiency improvement results", "theme": "department_operations", "id": 122},
    {"query": "machine learning operations scheduling optimization cost savings", "theme": "department_operations", "id": 123},
    {"query": "AI workflow automation operations productivity metrics deployment", "theme": "department_operations", "id": 124},
    {"query": "AI facility management building operations energy savings", "theme": "department_operations", "id": 125},
    {"query": "intelligent automation operations bottleneck identification case study", "theme": "department_operations", "id": 126},
    {"query": "AI operations monitoring anomaly detection downtime reduction", "theme": "department_operations", "id": 127},
    {"query": "AI capacity planning operations resource optimization ROI", "theme": "department_operations", "id": 128},

    # Department: HR (7 queries)
    {"query": "AI recruiting hiring automation time-to-fill reduction results", "theme": "department_hr", "id": 129},
    {"query": "machine learning employee retention prediction attrition reduction", "theme": "department_hr", "id": 130},
    {"query": "AI HR onboarding automation employee experience improvement", "theme": "department_hr", "id": 131},
    {"query": "AI skills assessment workforce planning talent analytics deployment", "theme": "department_hr", "id": 132},
    {"query": "generative AI HR policy document creation automation case study", "theme": "department_hr", "id": 133},
    {"query": "AI compensation benchmarking pay equity analysis metrics", "theme": "department_hr", "id": 134},
    {"query": "AI performance management review automation productivity ROI", "theme": "department_hr", "id": 135},

    # Department: Legal (7 queries)
    {"query": "AI legal contract review analysis time savings cost reduction", "theme": "department_legal", "id": 136},
    {"query": "AI legal research case law analysis automation deployment results", "theme": "department_legal", "id": 137},
    {"query": "NLP legal document drafting automation productivity improvement", "theme": "department_legal", "id": 138},
    {"query": "AI compliance monitoring regulatory change detection metrics", "theme": "department_legal", "id": 139},
    {"query": "AI e-discovery document review litigation cost savings case study", "theme": "department_legal", "id": 140},
    {"query": "AI intellectual property patent analysis search automation", "theme": "department_legal", "id": 141},
    {"query": "AI legal risk assessment prediction contract management ROI", "theme": "department_legal", "id": 142},

    # Department: Procurement (7 queries)
    {"query": "AI procurement spend analysis cost savings optimization results", "theme": "department_procurement", "id": 143},
    {"query": "machine learning supplier risk assessment procurement deployment", "theme": "department_procurement", "id": 144},
    {"query": "AI contract management procurement automation efficiency metrics", "theme": "department_procurement", "id": 145},
    {"query": "AI strategic sourcing negotiation optimization case study", "theme": "department_procurement", "id": 146},
    {"query": "AI procurement demand forecasting inventory optimization ROI", "theme": "department_procurement", "id": 147},
    {"query": "AI tail spend management procurement automation savings", "theme": "department_procurement", "id": 148},
    {"query": "AI supplier performance monitoring procurement intelligence", "theme": "department_procurement", "id": 149},

    # Department: R&D / Product (7 queries)
    {"query": "AI product development acceleration time-to-market improvement", "theme": "department_rd_product", "id": 150},
    {"query": "generative AI design prototyping iteration speed results", "theme": "department_rd_product", "id": 151},
    {"query": "AI materials discovery research simulation cost reduction", "theme": "department_rd_product", "id": 152},
    {"query": "machine learning experimental design optimization R&D efficiency", "theme": "department_rd_product", "id": 153},
    {"query": "AI product feedback analysis customer insights automation case study", "theme": "department_rd_product", "id": 154},
    {"query": "AI code generation software development productivity metrics", "theme": "department_rd_product", "id": 155},
    {"query": "AI testing automation QA software development deployment ROI", "theme": "department_rd_product", "id": 156},

    # Department: Strategy (7 queries)
    {"query": "AI competitive intelligence strategy analysis automation results", "theme": "department_strategy", "id": 157},
    {"query": "AI market research trend analysis strategic planning deployment", "theme": "department_strategy", "id": 158},
    {"query": "machine learning scenario planning business forecasting accuracy", "theme": "department_strategy", "id": 159},
    {"query": "AI M&A due diligence target analysis acceleration case study", "theme": "department_strategy", "id": 160},
    {"query": "generative AI strategy report executive briefing automation", "theme": "department_strategy", "id": 161},
    {"query": "AI business model innovation digital transformation metrics", "theme": "department_strategy", "id": 162},
    {"query": "AI portfolio optimization strategic resource allocation ROI", "theme": "department_strategy", "id": 163},

    # Department: Risk (7 queries)
    {"query": "AI enterprise risk management prediction detection improvement", "theme": "department_risk", "id": 164},
    {"query": "machine learning cybersecurity threat detection risk deployment", "theme": "department_risk", "id": 165},
    {"query": "AI operational risk monitoring early warning system results", "theme": "department_risk", "id": 166},
    {"query": "AI third-party risk assessment vendor management automation", "theme": "department_risk", "id": 167},
    {"query": "AI regulatory compliance risk monitoring automation case study", "theme": "department_risk", "id": 168},
    {"query": "predictive analytics business continuity risk planning metrics", "theme": "department_risk", "id": 169},
    {"query": "AI fraud detection enterprise risk reduction savings ROI", "theme": "department_risk", "id": 170},

    # Department: Quality (7 queries)
    {"query": "AI quality control inspection automation defect detection results", "theme": "department_quality", "id": 171},
    {"query": "computer vision quality assurance manufacturing deployment metrics", "theme": "department_quality", "id": 172},
    {"query": "AI statistical process control quality improvement case study", "theme": "department_quality", "id": 173},
    {"query": "machine learning root cause analysis quality issues resolution", "theme": "department_quality", "id": 174},
    {"query": "AI quality prediction preventive maintenance deployment ROI", "theme": "department_quality", "id": 175},
    {"query": "AI document quality compliance verification automation", "theme": "department_quality", "id": 176},
    {"query": "AI customer feedback quality sentiment analysis improvement", "theme": "department_quality", "id": 177},

    # Department: Training (7 queries)
    {"query": "AI corporate training personalized learning productivity results", "theme": "department_training", "id": 178},
    {"query": "generative AI training content creation automation cost savings", "theme": "department_training", "id": 179},
    {"query": "AI skills gap analysis learning path recommendation deployment", "theme": "department_training", "id": 180},
    {"query": "AI simulation training workforce upskilling engagement metrics", "theme": "department_training", "id": 181},
    {"query": "AI knowledge management corporate learning retention case study", "theme": "department_training", "id": 182},
    {"query": "AI coaching performance support employee development ROI", "theme": "department_training", "id": 183},
    {"query": "AI training assessment evaluation automation efficiency", "theme": "department_training", "id": 184},

    # Department: Pricing (7 queries)
    {"query": "AI dynamic pricing optimization revenue improvement results", "theme": "department_pricing", "id": 185},
    {"query": "machine learning price elasticity modeling competitive pricing", "theme": "department_pricing", "id": 186},
    {"query": "AI markdown optimization retail pricing profit improvement", "theme": "department_pricing", "id": 187},
    {"query": "AI B2B pricing negotiation optimization deal profitability case study", "theme": "department_pricing", "id": 188},
    {"query": "AI promotional pricing effectiveness measurement metrics", "theme": "department_pricing", "id": 189},
    {"query": "machine learning subscription pricing churn reduction deployment", "theme": "department_pricing", "id": 190},
    {"query": "AI pricing strategy competitive intelligence revenue ROI", "theme": "department_pricing", "id": 191},

    # Department: Demand Planning (7 queries)
    {"query": "AI demand planning forecasting accuracy improvement results", "theme": "department_demand_planning", "id": 192},
    {"query": "machine learning demand sensing supply chain optimization deployment", "theme": "department_demand_planning", "id": 193},
    {"query": "AI inventory optimization demand planning cost reduction metrics", "theme": "department_demand_planning", "id": 194},
    {"query": "AI new product demand forecasting launch planning case study", "theme": "department_demand_planning", "id": 195},
    {"query": "AI seasonal demand planning promotional forecasting improvement", "theme": "department_demand_planning", "id": 196},
    {"query": "machine learning demand planning stockout reduction customer service", "theme": "department_demand_planning", "id": 197},
    {"query": "AI demand planning collaboration consensus forecasting ROI", "theme": "department_demand_planning", "id": 198},
]


AI_EXA_THEMES: List[str] = [
    # Industry themes (20)
    "industry_retail", "industry_manufacturing", "industry_supply_chain",
    "industry_construction", "industry_healthcare", "industry_pharma",
    "industry_financial_services", "industry_insurance", "industry_energy",
    "industry_telecom", "industry_transportation", "industry_agriculture",
    "industry_real_estate", "industry_hospitality", "industry_media",
    "industry_professional_services", "industry_cpg", "industry_aerospace",
    "industry_automotive", "industry_food_beverage",
    # Department themes (14)
    "department_marketing", "department_finance", "department_sales",
    "department_operations", "department_hr", "department_legal",
    "department_procurement", "department_rd_product", "department_strategy",
    "department_risk", "department_quality", "department_training",
    "department_pricing", "department_demand_planning",
]


def get_ai_queries_by_theme(theme: str) -> List[Dict[str, Any]]:
    """Get AI Exa queries filtered by theme."""
    return [q for q in AI_EXA_QUERIES if q["theme"] == theme]


def get_all_ai_query_strings() -> List[str]:
    """Get all query strings (for cost estimation)."""
    return [q["query"] for q in AI_EXA_QUERIES]
