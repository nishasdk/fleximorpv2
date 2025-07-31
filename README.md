# FlexiMORP v2 - Offshore Renewable Energy Optimization Platform

## 🌊 Advanced Multi-Step Analysis for Offshore Renewable Systems

FlexiMORP v2 is a comprehensive Python platform for optimizing offshore renewable energy systems through a structured 4-step analysis framework with real options analysis and uncertainty quantification.

## 🚀 Key Features

### Core Analysis Framework
1. **Baseline Optimization** - Deterministic optimal design under perfect information
2. **Uncertainty Analysis** - Monte Carlo simulation with robust optimization
3. **Flexible Design** - Real options analysis with expansion/abandonment strategies  
4. **Sensitivity Analysis** - Parameter importance and risk factor identification

### Technology Support
- **Wind Energy** - Offshore wind turbines with variable capacity factors
- **Solar Energy** - Floating solar PV systems
- **Wave Energy** - Wave energy converters for high-energy sites

### Data Integration
- **NASA API** - Climate data and weather patterns
- **NREL API** - Renewable resource assessment and technology data
- **Copernicus API** - European marine and atmospheric data
- **OpenWeather API** - Real-time weather and forecasting
- **Intelligent Caching** - Multi-level caching system for performance

## 📁 Project Structure

```
fleximorpv2/
├── fleximorpv2/                   # Core Python package
│   ├── baseline_optimization.py   # Step 1: Deterministic optimization
│   ├── uncertainty_analysis.py    # Step 2: Monte Carlo & robust optimization
│   ├── flexible_design.py         # Step 3: Real options analysis
│   ├── sensitivity_analysis.py    # Step 4: Parameter sensitivity
│   ├── config.py                 # Configuration management
│   ├── graphics.py               # Visualization utilities
│   ├── api/                      # API integration layer
│   │   ├── base_api.py          # Common API functionality
│   │   ├── cache_manager.py     # Intelligent caching
│   │   ├── nasa_api.py          # NASA climate data
│   │   ├── nrel_api.py          # NREL resource data
│   │   ├── copernicus_api.py    # Copernicus marine data
│   │   └── openweather_api.py   # Real-time weather
│   ├── models/                   # Core models
│   │   ├── platform.py          # Platform design model
│   │   ├── technologies.py      # Technology performance models
│   │   └── economics.py         # Economic evaluation
│   └── utils/                    # Utilities
│       ├── data_loader.py       # API data integration
│       ├── optimization.py      # Optimization algorithms
│       ├── financial.py         # Financial calculations
│       ├── environmental.py     # Environmental assessment
│       ├── decision_trees.py    # Real options modeling
│       └── visualization.py     # Advanced plotting
├── data/                         # Case study data
│   ├── alaska/                  # Alaska remote community case
│   │   ├── config.yaml          # Site configuration
│   │   ├── inputs/              # Input data and constraints
│   │   └── results/             # Analysis results
│   ├── blyth/                   # Blyth offshore wind case
│   └── eastport/                # Eastport fishing-constrained case
├── notebooks/                    # Jupyter analysis notebooks
├── webapp/                       # Streamlit web application
│   ├── app.py                   # Main web interface
│   ├── components/              # UI components
│   ├── pages/                   # Multi-page interface
│   └── assets/                  # Static assets
├── tests/                        # Unit and integration tests
├── cache/                        # API response caching
│   ├── nasa/                    # NASA data cache
│   ├── nrel/                    # NREL data cache
│   ├── copernicus/              # Copernicus cache
│   └── openweather/             # OpenWeather cache
└── docs/                         # Documentation
```

## 🔧 Installation and Setup

### Prerequisites
- Python 3.8+
- Git

### Quick Start
```bash
# Clone repository
git clone https://github.com/your-org/fleximorpv2.git
cd fleximorpv2

# Install dependencies
pip install -r requirements.txt

# Run web application
streamlit run webapp/app.py

# Or run example analysis
python example_integration.py
```

### API Configuration (Optional)
The system includes demo data, but for live analysis obtain free API keys:

- **NREL**: [developer.nrel.gov](https://developer.nrel.gov)
- **NASA**: [api.nasa.gov](https://api.nasa.gov)  
- **OpenWeather**: [openweathermap.org](https://openweathermap.org/api)
- **Copernicus**: [climate.copernicus.eu](https://climate.copernicus.eu)

## 🌍 Case Studies

### Alaska Remote Community
- **Focus**: Energy independence for remote Arctic community
- **Challenges**: Extreme weather, sea ice, indigenous consultation
- **Technologies**: Wind + Solar (wave excluded due to ice)
- **Key Constraints**: Environmental sensitivity, community ownership

### Blyth Offshore Wind Farm
- **Focus**: Large-scale commercial offshore development  
- **Challenges**: Grid integration, marine ecology, fishing conflicts
- **Technologies**: Wind + Solar + Wave hybrid system
- **Key Constraints**: Commercial fishing areas, shipping lanes

### Eastport Fishing-Constrained
- **Focus**: Development with significant stakeholder conflicts
- **Challenges**: Fishing industry opposition, seasonal restrictions
- **Technologies**: Wind + Solar + Wave with flexible deployment
- **Key Constraints**: Critical fishing areas, lobster migration

## 🚀 Usage Examples

### Web Interface
```bash
streamlit run webapp/app.py
# Navigate to http://localhost:8501
```

### Programmatic Analysis
```python
from fleximorpv2 import BaselineOptimization, UncertaintyAnalysis
from fleximorpv2.config import load_site_config

# Load site configuration
config = load_site_config("blyth")

# Step 1: Baseline optimization
baseline = BaselineOptimization(config)
baseline_results = baseline.optimize(
    target_type="capacity", 
    target_value=100  # 100 MW target
)

# Step 2: Uncertainty analysis  
uncertainty = UncertaintyAnalysis(config)
uncertainty_results = uncertainty.analyze_uncertainty(
    baseline_design=baseline_results.optimal_design,
    reoptimize=True
)

# Display results
print(f"Baseline LCOE: £{baseline_results.financial_metrics['lcoe']:.2f}/MWh")
print(f"Mean LCOE under uncertainty: £{uncertainty_results.mean_performance['lcoe']:.2f}/MWh")
print(f"LCOE 95% VaR: £{uncertainty_results.risk_metrics['lcoe_var_95']:.2f}/MWh")
```

### Complete 4-Step Workflow
```python
from fleximorpv2 import run_complete_analysis

# Run all 4 steps for a site
results = run_complete_analysis(
    site="blyth",
    target_type="capacity",
    target_value=100,
    save_results=True
)

# Access results from each step
baseline = results['baseline']
uncertainty = results['uncertainty'] 
flexibility = results['flexibility']
sensitivity = results['sensitivity']
```

## 📊 Analysis Outputs

### Step 1: Baseline Results
- Optimal technology mix and capacities
- Economic metrics (LCOE, NPV, IRR, payback period)
- Technical performance (capacity factors, energy yield)
- Platform design parameters (size, depth, distance to shore)

### Step 2: Uncertainty Results  
- Monte Carlo simulation results (1000+ scenarios)
- Risk metrics (VaR, CVaR, probability distributions)
- Robust optimal design under uncertainty
- Parameter correlation analysis

### Step 3: Flexibility Results
- Real options valuation (expansion, abandonment, switching)
- Optimal staging strategy and timing
- Value of flexibility quantification
- Decision trees and trigger strategies

### Step 4: Sensitivity Results
- Parameter importance ranking
- Tornado diagrams and sensitivity indices
- Critical parameter identification
- Robustness assessment

## 🔄 Analysis Workflow

1. **Site Configuration** → Load case study or define custom site
2. **Target Definition** → Set capacity, energy, or cost optimization target  
3. **Baseline Optimization** → Find deterministic optimal design
4. **Uncertainty Analysis** → Assess performance under uncertainty
5. **Flexibility Planning** → Value real options and staging strategies
6. **Sensitivity Analysis** → Identify critical parameters and risks
7. **Results Export** → Generate reports and visualizations

## 🧪 Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Tests  
```bash
python example_integration.py
```

### Web Application
```bash
streamlit run webapp/app.py
# Test complete workflow through UI
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NREL** - Renewable resource data and technology databases
- **NASA** - Climate and weather data services  
- **Copernicus** - European environmental monitoring program
- **OpenWeather** - Real-time weather data services
- **Streamlit** - Interactive web application framework

## 📞 Support

- **Documentation**: `/docs` directory
- **Issues**: GitHub Issues tracker
- **Email**: support@fleximorp.org

---

**FlexiMORP v2** - Production-ready offshore renewable energy optimization platform with comprehensive uncertainty analysis, real options valuation, and interactive web interface.
