# FlexiMORP v2 - Offshore Renewable Energy Optimization Platform

## 🌊 Advanced Multi-Step Analysis for Offshore Renewable Systems

An expansion from v1 - FlexiMORP v2 is a comprehensive Python platform for optimizing offshore renewable energy systems through a structured 4-step analysis framework with real options analysis and uncertainty quantification.

## 🚀 Key Features

### Core Analysis Framework
1. **Baseline Optimization** - Deterministic optimal design under perfect information
2. **Uncertainty Analysis** - Monte Carlo and Latin Hypercube sampling with robust optimization
3. **Flexible Design** - Real options analysis with expansion/abandonment strategies  
4. **Sensitivity Analysis** - Parameter importance and risk factor identification

### Advanced Uncertainty Analysis
- **Monte Carlo Simulation** - Traditional random sampling for uncertainty quantification
- **Latin Hypercube Sampling** - Improved space coverage with faster convergence
- **Sampling Method Comparison** - Built-in tools to compare convergence and accuracy
- **Robust Optimization** - Find designs that perform well across uncertainty scenarios

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

# Run tests to verify installation
python -m pytest tests/ -v

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
- **Analysis**: TRIO optimization with MCDA (LCOE, emissions, social acceptance, aquaculture synergy)

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

# Step 2: Uncertainty analysis with sampling method choice
uncertainty = UncertaintyAnalysis(config)

# Use Monte Carlo sampling
mc_results = uncertainty.analyze_uncertainty(
    baseline_design=baseline_results.optimal_design,
    sampling_method='monte_carlo',
    reoptimize=True
)

# Use Latin Hypercube sampling
lhs_results = uncertainty.analyze_uncertainty(
    baseline_design=baseline_results.optimal_design,
    sampling_method='latin_hypercube',
    reoptimize=True
)

# Compare sampling methods
comparison = uncertainty.compare_sampling_methods(
    baseline_design=baseline_results.optimal_design,
    n_runs=1000
)

# Display results
print(f"Baseline LCOE: £{baseline_results.financial_metrics['lcoe']:.2f}/MWh")
print(f"Monte Carlo LCOE: £{mc_results.mean_performance['lcoe']:.2f}/MWh")
print(f"Latin Hypercube LCOE: £{lhs_results.mean_performance['lcoe']:.2f}/MWh")
print(f"Convergence: {comparison['convergence_analysis']['recommendation']}")
```

### Complete 4-Step Workflow
```python
from fleximorpv2 import run_complete_analysis

# Run all 4 steps for a site
results = run_complete_analysis(
    site="alaska",
    target_type="capacity",
    target_value=100,
    sampling_method="latin_hypercube",  # Choose sampling method
    save_results=True
)

# Access results from each step
baseline = results['baseline']
uncertainty = results['uncertainty'] 
flexibility = results['flexibility']
sensitivity = results['sensitivity']
```

### TRIO-MCDA Analysis (Alaska Case Study)
```python
# Run comprehensive TRIO-MCDA analysis
exec(open('notebooks/alaska_complete_analysis.py').read())

# Or use Jupyter notebook for interactive analysis
# jupyter notebook notebooks/alaska_trio_mcda_analysis.ipynb
```

## 📊 Analysis Outputs

### Step 1: Baseline Results
- Optimal technology mix and capacities
- Economic metrics (LCOE, NPV, IRR, payback period)
- Technical performance (capacity factors, energy yield)
- Platform design parameters (size, depth, distance to shore)

### Step 2: Uncertainty Results  
- **Monte Carlo**: Traditional random sampling results
- **Latin Hypercube**: Improved sampling with better convergence
- Risk metrics (VaR, CVaR, probability distributions)
- Robust optimal design under uncertainty
- Parameter correlation analysis
- Sampling method comparison and convergence analysis

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
4. **Uncertainty Analysis** → Choose sampling method and assess performance under uncertainty
5. **Flexibility Planning** → Value real options and staging strategies
6. **Sensitivity Analysis** → Identify critical parameters and risks
7. **Results Export** → Generate reports and visualizations

## 🧪 Testing

FlexiMORP v2 includes a comprehensive test suite to ensure reliability and correctness.

### Running Tests

#### All Tests
```bash
# Run complete test suite
python -m pytest tests/ -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=fleximorpv2 --cov-report=term-missing

# Run using test runner script
python tests/run_tests.py
```

#### Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/ -v -m unit

# Integration tests only  
python -m pytest tests/ -v -m integration

# Slow tests (Monte Carlo simulations)
python -m pytest tests/ -v -m slow

# API tests (require network access)
python -m pytest tests/ -v -m api
```

### Test Structure

- **`conftest.py`** - Pytest configuration, fixtures, and test utilities
- **`test_baseline_optimization.py`** - Unit tests for optimization algorithms
- **`test_uncertainty_analysis.py`** - Tests for Monte Carlo and Latin Hypercube sampling
- **`test_integration.py`** - End-to-end workflow tests
- **`test_mcda_analysis.py`** - TRIO optimization and MCDA functionality tests
- **`run_tests.py`** - Test runner with multiple execution modes

### Test Coverage

The test suite covers:
- ✅ Core optimization algorithms and constraint handling
- ✅ Uncertainty analysis with both sampling methods
- ✅ MCDA analysis with entropy weighting and TOPSIS
- ✅ Configuration loading and validation
- ✅ API integration (with mocking)
- ✅ Complete workflow integration
- ✅ Results serialization and file I/O
- ✅ Error handling and edge cases

### Example Test Usage
```bash
# Quick verification after installation
python test_sampling_methods.py

# Full test suite with verbose output
python -m pytest tests/ -v --tb=short

# Test specific functionality
python -m pytest tests/test_uncertainty_analysis.py::TestUncertaintyAnalysis::test_latin_hypercube_sampling -v
```

## 🎯 Sampling Method Comparison

FlexiMORP v2 supports advanced sampling methods for uncertainty analysis:

### Monte Carlo Sampling
- **Traditional approach**: Random sampling from distributions
- **Use case**: General uncertainty analysis, well-understood method
- **Convergence**: O(1/√n) convergence rate

### Latin Hypercube Sampling  
- **Advanced approach**: Stratified sampling ensuring better space coverage
- **Use case**: When faster convergence is needed or sample budget is limited
- **Convergence**: Often superior convergence with fewer samples

### When to Use Each Method
- **Monte Carlo**: Standard analysis, comparing with literature, simple implementation
- **Latin Hypercube**: Limited computational budget, need faster convergence, high-dimensional problems
- **Both**: Use comparison tool to determine which performs better for your specific case

```python
# Test both methods and compare
comparison = uncertainty_analyzer.compare_sampling_methods(
    baseline_design=design,
    n_runs=500  # Compare with 500 samples each
)
print(f"Recommendation: {comparison['convergence_analysis']['recommendation']}")
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. **Run tests** (`python -m pytest tests/`)
5. Push to branch (`git push origin feature/new-feature`)
6. Open Pull Request

### Development Guidelines
- Write tests for new functionality
- Follow existing code style and patterns
- Update documentation for new features
- Ensure all tests pass before submitting PR

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NREL** - Renewable resource data and technology databases
- **NASA** - Climate and weather data services  
- **Copernicus** - European environmental monitoring program
- **OpenWeather** - Real-time weather data services
- **Streamlit** - Interactive web application framework
- **SciPy** - Scientific computing including Latin Hypercube sampling

## 📞 Support

- **Documentation**: `/docs` directory and inline docstrings
- **Issues**: GitHub Issues tracker
- **Tests**: Run `python -m pytest tests/` to verify functionality
- **Examples**: See `notebooks/` and `example_integration.py`

## 📁 Project Structure

```
fleximorpv2/
├── fleximorpv2/                   # Core Python package
│   ├── baseline_optimization.py   # Step 1: Deterministic optimization
│   ├── uncertainty_analysis.py    # Step 2: Monte Carlo & Latin Hypercube sampling
│   ├── flexible_design.py         # Step 3: Real options analysis
│   ├── sensitivity_analysis.py    # Step 4: Parameter sensitivity
│   ├── config.py                 # Configuration management
│   ├── graphics.py               # Visualization utilities
│   ├── api/                      # API integration layer
│   │   ├── __init__.py
│   │   ├── base_api.py          # Common API functionality
│   │   ├── cache_manager.py     # Intelligent caching
│   │   ├── nasa_api.py          # NASA climate data
│   │   ├── nrel_api.py          # NREL resource data
│   │   ├── copernicus_api.py    # Copernicus marine data
│   │   └── openweather_api.py   # Real-time weather
│   ├── models/                   # Core models
│   │   ├── __init__.py
│   │   ├── platform.py          # Platform design model
│   │   ├── technologies.py      # Technology performance models
│   │   └── economics.py         # Economic evaluation
│   └── utils/                    # Utilities
│       ├── __init__.py
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
│   │   │   ├── environmental_constraints.py
│   │   │   ├── stakeholder_preferences.py
│   │   │   └── weather_data.csv
│   │   └── results/             # Analysis results
│   │       ├── baseline/        # Baseline optimization results
│   │       ├── uncertainty/     # Uncertainty analysis results
│   │       ├── flexible/        # Flexible design results
│   │       └── sensitivity/     # Sensitivity analysis results
│   ├── blyth/                   # Blyth offshore wind case
│   │   ├── config.yaml
│   │   ├── inputs/
│   │   └── results/
│   │       ├── baseline/
│   │       ├── uncertainty/
│   │       ├── flexible/
│   │       └── sensitivity/
│   └── eastport/                # Eastport fishing-constrained case
│       ├── config.yaml
│       ├── inputs/
│       └── results/
├── notebooks/                    # Jupyter analysis notebooks
│   ├── alaska_trio_mcda_analysis.ipynb     # Alaska TRIO-MCDA analysis
│   ├── alaska_complete_analysis.py         # Complete Alaska analysis script
│   ├── blyth_analysis.ipynb               # Blyth case study (planned)
│   └── eastport_analysis.ipynb            # Eastport case study (planned)
├── webapp/                       # Streamlit web application
│   ├── app.py                   # Main web interface
│   ├── components/              # UI components
│   ├── pages/                   # Multi-page interface
│   └── assets/                  # Static assets
├── tests/                        # Comprehensive test suite
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── run_tests.py             # Test runner script
│   ├── test_baseline_optimization.py      # Baseline optimization tests
│   ├── test_uncertainty_analysis.py       # Uncertainty analysis tests
│   ├── test_integration.py                # End-to-end workflow tests
│   └── test_mcda_analysis.py              # TRIO-MCDA functionality tests
├── cache/                        # API response caching
│   ├── nasa/                    # NASA data cache
│   ├── nrel/                    # NREL data cache
│   ├── copernicus/              # Copernicus cache
│   └── openweather/             # OpenWeather cache
├── docs/                         # Documentation
├── requirements.txt              # Python dependencies
├── example_integration.py        # Example usage script
├── test_sampling_methods.py      # Sampling method comparison test
└── README.md                    # This file
```

---

**FlexiMORP v2** - Production-ready offshore renewable energy optimization platform with comprehensive uncertainty analysis, advanced sampling methods, real options valuation, and interactive web interface.
