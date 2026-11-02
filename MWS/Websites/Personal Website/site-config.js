/* Owner control: set foundingOffer.enabled to false to close introductory pricing.
Track eligibility in actual business records; never infer availability from site visits. */
window.MWS_CONFIG = {
  "foundingOffer": {
    "enabled": true
  },
  "services": [
    {
      "id": "cleanup",
      "name": "Spreadsheet & Data Cleanup",
      "regular": 99,
      "intro": 69,
      "summary": "Turn inconsistent spreadsheets into records you can actually use.",
      "examples": [
        "Remove duplicate records",
        "Standardize formatting and validate inconsistencies",
        "Clean Excel and CSV files",
        "Organize customer records and merge compatible spreadsheets"
      ],
      "scope": [
        "One dataset or workbook, up to 5,000 rows",
        "Basic cleaning and formatting",
        "One completed output file",
        "One revision for agreed requirements"
      ],
      "custom": "Complex transformations, manual research, extensive missing-data reconstruction, and additional files."
    },
    {
      "id": "inventory",
      "name": "Inventory & Product Data Management",
      "regular": 199,
      "intro": 149,
      "summary": "Give your product catalog a consistent, dependable structure.",
      "examples": [
        "Identify duplicate SKUs",
        "Standardize product names and attributes",
        "Prepare Shopify-compatible import files",
        "Consolidate inventory exports and identify inconsistent records"
      ],
      "scope": [
        "One product dataset, up to 2,500 rows",
        "Basic SKU and attribute validation",
        "One standardized export",
        "One revision"
      ],
      "custom": "Live platform integrations, inventory reconciliation across systems, and complex product matching."
    },
    {
      "id": "automation",
      "name": "Business Workflow Automation",
      "regular": 299,
      "intro": 229,
      "summary": "Make recurring reports and repetitive admin easier to handle.",
      "examples": [
        "Automate spreadsheet processing",
        "Combine recurring reports",
        "Generate routine summaries",
        "Transform business exports with small Python utilities"
      ],
      "scope": [
        "One defined workflow",
        "Up to two input formats and one output format",
        "Basic documentation",
        "One revision"
      ],
      "custom": "Complex API integrations, authentication, hosting, ongoing support, and multi-system workflows."
    },
    {
      "id": "reporting",
      "name": "Reports & Dashboards",
      "regular": 249,
      "intro": 189,
      "summary": "See what matters in your sales, inventory, and business data.",
      "examples": [
        "Sales summaries and business KPIs",
        "Inventory performance reports",
        "Trend analysis and product comparisons",
        "Simple interactive visualizations"
      ],
      "scope": [
        "One supplied dataset",
        "Up to five defined metrics and three visualizations",
        "One dashboard or report",
        "One revision"
      ],
      "custom": "Live data connections, hosted dashboards, complex forecasting, and advanced permissions."
    },
    {
      "id": "analytics",
      "name": "Custom Algorithms & Business Analytics",
      "regular": 399,
      "intro": 299,
      "summary": "Explore a specific business question with a focused proof of concept.",
      "examples": [
        "Product similarity matching and duplicate detection",
        "Customer or product segmentation",
        "Classification models and basic forecasting analysis",
        "Rule-based decisions and custom processing algorithms"
      ],
      "scope": [
        "One clearly defined business problem",
        "Initial dataset review",
        "One small proof of concept",
        "Basic evaluation, findings, and one results report"
      ],
      "custom": "Advanced modeling, production deployment, integrations, ongoing model monitoring, large datasets, and extensive experimentation. This package is not a complete production machine learning system. No accuracy, revenue, or outcome guarantees."
    }
  ]
};
