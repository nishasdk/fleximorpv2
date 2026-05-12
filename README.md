# FlexiMORP v2 - Offshore Renewable Energy Optimization Platform

An expansion of FlexiMORP v1. Python platform for optimizing offshore renewable energy systems with Monte Carlo uncertainty analysis, real options valuation, and multi-objective Pareto optimization across wind, solar, wave, and tidal technologies.

> **Early development notice:** This project is in a very early stage. All outputs are rough approximations only. Do not use this tool for any actual investment, engineering, or policy analysis. Features and accuracy are being progressively refined.

## Key Features

### Analysis Pipeline
1. **Baseline Optimization** - Deterministic optimal design under perfect information
2. **Uncertainty Analysis** - Monte Carlo and Latin Hypercube sampling with robust optimization
3. **Flexible Design** - Real options analysis with expansion/abandonment strategies
4. **Multi-Objective Analysis** - Pareto frontier across LCOE, NPV, environmental impact, and risk
5. **Sensitivity Analysis** - Parameter importance and risk factor identification
6. **Visualization** - Interactive plots and deployment rollout planning

### Uncertainty Analysis
- **Monte Carlo Simulation** - Traditional random sampling for uncertainty quantification
- **Latin Hypercube Sampling** - Stratified sampling with faster convergence
- **Sampling Method Comparison** - Built-in convergence comparison tools
- **Robust Optimization** - Designs that perform well across uncertainty scenarios

### Technology Support
- **Wind Energy** - Offshore wind turbines with variable capacity factors
- **Solar Energy** - Floating and land-mounted solar PV
- **Wave Energy** - Wave energy converters for high-energy open-ocean sites
- **Tidal Energy** - Tidal stream turbines (cross-flow helical, e.g. ORPC TidGen)

### Data Integration
- **NASA API** - Climate data and weather patterns
- **NREL API** - Renewable resource assessment and technology data
- **Copernicus API** - European marine and atmospheric data
- **OpenWeather API** - Real-time weather and forecasting
- **Intelligent Caching** - Multi-level caching system for performance

## Installation and Setup

### Prerequisites
- Python 3.8+
- Git

### Quick Start
```bash
git clone https://github.com/nishasdk/fleximorpv2.git
cd fleximorpv2

pip install -r requirements.txt

# Run tests to verify installation
python -m pytest tests/ -v

# Run web application
streamlit run webapp/app.py
```

### API Configuration (Optional)
The system includes synthetic demo data. For live resource assessment, obtain free API keys:

- **NREL**: [developer.nrel.gov](https://developer.nrel.gov)
- **NASA**: [api.nasa.gov](https://api.nasa.gov)
- **OpenWeather**: [openweathermap.org](https://openweathermap.org/api)
- **Copernicus**: [climate.copernicus.eu](https://climate.copernicus.eu)

## Case Studies

### Alaska - Igiugig Remote Community
- **Focus**: Energy independence for a remote Yup'ik community on the Kvichak River
- **Challenges**: Extreme weather, sea ice, riverine siting, indigenous consultation
- **Technologies**: Wind + Solar + Tidal/Hydro (river flow turbines)
- **Key Constraints**: Salmon spawning grounds, traditional fishing areas, community ownership
- **Analysis**: TRIO optimization with MCDA (LCOE, emissions, social acceptance, aquaculture synergy)

### Blyth - Offshore Wind Farm
- **Focus**: Large-scale commercial offshore development in the North Sea
- **Challenges**: Grid integration, marine ecology, fishing conflicts
- **Technologies**: Wind + Solar + Wave hybrid system
- **Key Constraints**: Commercial fishing areas, shipping lanes

### Eastport, Maine - Tidal-Constrained Site
- **Focus**: Development alongside active lobster fishing industry
- **Challenges**: Fishing industry co-existence, seasonal restrictions, permitting
- **Technologies**: Wind + Solar + Tidal (ORPC TidGen, Western Passage)
- **Key Constraints**: Lobster grounds, Passamaquoddy tribal interests, ferry routes
- **Reference**: [ORPC Western Passage project](https://orpc.co) - first grid-connected tidal installation in North America

## Usage Examples

### Web Interface
```bash
streamlit run webapp/app.py
# Navigate to http://localhost:8501
```

### Programmatic Analysis
```python
from fleximorpv2 import BaselineOptimization, UncertaintyAnalysis
from fleximorpv2.config import load_config

config = load_config("blyth")

# Step 1: Baseline optimization
baseline = BaselineOptimization(config)
baseline_results = baseline.optimize(
    target_type="production",
    target_value=876000  # kWh target
)

# Step 2: Uncertainty analysis
uncertainty = UncertaintyAnalysis(config)

mc_results = uncertainty.analyze_uncertainty(
    baseline_design=baseline_results.optimal_design,
    sampling_method='monte_carlo',
    reoptimize=False
)

lhs_results = uncertainty.analyze_uncertainty(
    baseline_design=baseline_results.optimal_design,
    sampling_method='latin_hypercube',
    reoptimize=False
)

comparison = uncertainty.compare_sampling_methods(
    baseline_design=baseline_results.optimal_design,
    n_runs=500
)

print(f"Baseline LCOE: {baseline_results.financial_metrics['lcoe']:.2f}/MWh")
print(f"Monte Carlo LCOE: {mc_results.mean_performance['lcoe']:.2f}/MWh")
print(f"Latin Hypercube LCOE: {lhs_results.mean_performance['lcoe']:.2f}/MWh")
print(f"Convergence: {comparison['convergence_analysis']['recommendation']}")
```

### Alaska Notebook
```bash
jupyter notebook notebooks/alaska_analysis.ipynb
```

## Analysis Outputs

### Step 1: Baseline Results
- Optimal technology mix and capacities
- Economic metrics (LCOE, NPV, IRR, payback period)
- Technical performance (capacity factors, energy yield)
- Platform design parameters (size, depth, distance to shore)

### Step 2: Uncertainty Results
- Monte Carlo and Latin Hypercube sampling results
- Risk metrics (VaR, CVaR, probability of loss)
- Robust optimal design under uncertainty
- Sampling method convergence comparison

### Step 3: Flexibility Results
- Real options valuation (expansion, abandonment, switching)
- Optimal staging strategy and deployment timeline
- Value of flexibility quantification
- Decision triggers and exercise probabilities

### Step 4: Multi-Objective Results
- Pareto frontier across competing objectives
- Trade-off analysis (LCOE vs NPV vs environmental impact)
- Non-dominated solution set

### Step 5: Sensitivity Results
- Parameter importance ranking
- Tornado diagrams and sensitivity indices
- Critical parameter identification
- Robustness assessment

## Testing

```bash
# Full test suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=fleximorpv2 --cov-report=term-missing

# Specific categories
python -m pytest tests/ -v -m unit
python -m pytest tests/ -v -m integration
```

### Test Coverage
- Baseline optimization algorithms and constraint handling
- Uncertainty analysis - Monte Carlo and Latin Hypercube sampling
- MCDA analysis with entropy weighting and TOPSIS
- Configuration loading and validation
- Sensitivity analysis parameter rankings
- Sampling method comparison
- End-to-end workflow integration _(planned)_
- API integration tests _(planned)_

## Sampling Method Comparison

### Monte Carlo Sampling
- **Approach**: Random sampling from distributions
- **Use case**: General uncertainty analysis, well-understood method
- **Convergence**: O(1/sqrt(n))

### Latin Hypercube Sampling
- **Approach**: Stratified sampling ensuring better space coverage
- **Use case**: Limited computational budget, faster convergence
- **Convergence**: Often superior with fewer samples

```python
comparison = uncertainty_analyzer.compare_sampling_methods(
    baseline_design=design,
    n_runs=500
)
print(f"Recommendation: {comparison['convergence_analysis']['recommendation']}")
```

## Roadmap

- [ ] Interactive map for site selection
- [ ] Customisable technology variables in the web interface
- [ ] Blyth and Eastport Jupyter notebooks
- [ ] End-to-end integration test suite
- [ ] Live API integration (NREL, NASA, Copernicus)
- [ ] Full NSGA-II multi-objective algorithm (currently random search + Pareto filter)
- [ ] SALib-based Sobol sensitivity indices
- [ ] Environmental assessment module (currently stub)
- [ ] Results export to PDF/Excel

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Run tests (`python -m pytest tests/`)
5. Push to branch and open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- **NREL** - Renewable resource data and technology databases
- **NASA** - Climate and weather data services
- **Copernicus** - European environmental monitoring program
- **OpenWeather** - Real-time weather data services
- **ORPC** - Tidal energy reference project, Eastport ME
- **Streamlit** - Interactive web application framework
- **SciPy** - Scientific computing including Latin Hypercube sampling
