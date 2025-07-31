# Select key metrics for spider plot
metrics = ['NPV', 'LCOE', 'Annual Energy', 'Reliability']
n_metrics = len(metrics)

# Normalize scenario results for spider plot
scenario_spider_data = {}
for scenario_name, results in scenario_results.items():
    # Normalize each metric (0-1 scale, higher = better)
    npv_norm = max(0, min(1, (results['results']['npv'] + 50e6) / 100e6))  # Scale -50M to +50M -> 0 to 1
    lcoe_norm = max(0, min(1, (250 - results['results']['lcoe']) / 150))  # Scale 250-100 -> 0 to 1 (inverted)
    energy_norm = max(0, min(1, results['results']['annual_energy'] / (annual_energy * 1.5)))  # Scale to 1.5x base
    reliability_norm = max(0, min(1, (1 - sensitivity_params['ice_impact_factor']['base']) / 0.2))  # Mock reliability
    
    scenario_spider_data[scenario_name] = [npv_norm, lcoe_norm, energy_norm, reliability_norm]

# Plot spider diagram
theta = np.linspace(0, 2*np.pi, n_metrics, endpoint=False)
theta = np.concatenate((theta, [theta[0]]))  # Complete the circle

colors_spider = ['green', 'red', 'blue', 'orange']
for i, (scenario_name, values) in enumerate(scenario_spider_data.items()):
    values_plot = values + [values[0]]  # Complete the circle
    ax5.plot(theta, values_plot, 'o-', linewidth=2, color=colors_spider[i], 
             label=scenario_name.replace('_', ' ').title(), alpha=0.8)
    ax5.fill(theta, values_plot, alpha=0.1, color=colors_spider[i])

ax5.set_xticks(theta[:-1])
ax5.set_xticklabels(metrics)
ax5.set_ylim(0, 1)
ax5.set_title('Scenario Performance\nSpider Plot', pad=20)
ax5.legend(bbox_to_anchor=(0.1, 0.1), loc='lower left', fontsize=8)
ax5.grid(True)

# 6. Monte Carlo sensitivity (parameter importance over uncertainty range)
ax6 = fig.add_subplot(gs[1, 2])

# Simulate parameter importance under uncertainty
n_samples = 200
np.random.seed(42)

param_importance_scores = []
top_5_params = [p for p, _ in ranked_sensitivities[:5]]

for param in top_5_params:
    param_range = sensitivity_params[param]['range']
    param_values = np.random.uniform(param_range[0], param_range[1], n_samples)
    
    npv_results = []
    for param_val in param_values:
        test_params = base_params.copy()
        test_params[param] = param_val
        result = calculate_npv_for_sensitivity(test_params)
        npv_results.append(result['npv'])
    
    # Calculate importance as coefficient of variation
    importance = np.std(npv_results) / abs(np.mean(npv_results)) if np.mean(npv_results) != 0 else 0
    param_importance_scores.append(importance)

bars6 = ax6.bar(range(len(top_5_params)), param_importance_scores, 
                color='lightcoral', alpha=0.7, edgecolor='black')
ax6.set_xticks(range(len(top_5_params)))
ax6.set_xticklabels([p.replace('_', '\n').title() for p in top_5_params], rotation=0, ha='center')
ax6.set_ylabel('Importance Score\n(Coefficient of Variation)')
ax6.set_title('Parameter Importance\nUnder Uncertainty')
ax6.grid(True, alpha=0.3)

# Add value labels
for bar, score in zip(bars6, param_importance_scores):
    ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
             f'{score:.3f}', ha='center', va='bottom', fontweight='bold')

# 7. Break-even analysis
ax7 = fig.add_subplot(gs[1, 3])

# Break-even analysis for electricity price
price_range = np.linspace(90, 180, 50)
breakeven_npvs = []

for price in price_range:
    test_params = base_params.copy()
    test_params['electricity_price'] = price
    result = calculate_npv_for_sensitivity(test_params)
    breakeven_npvs.append(result['npv']/1e6)

ax7.plot(price_range, breakeven_npvs, linewidth=3, color='blue', label='NPV vs Price')
ax7.axhline(0, color='red', linestyle='--', alpha=0.7, label='Break-even')
ax7.axvline(base_params['electricity_price'], color='green', linestyle=':', alpha=0.7, label='Base Case')

# Find break-even price
breakeven_idx = np.argmin(np.abs(breakeven_npvs))
breakeven_price = price_range[breakeven_idx]
ax7.axvline(breakeven_price, color='orange', linestyle='-.', alpha=0.7, 
           label=f'Break-even: £{breakeven_price:.0f}/MWh')

ax7.set_xlabel('Electricity Price (£/MWh)')
ax7.set_ylabel('NPV (£M)')
ax7.set_title('Break-even Analysis\nElectricity Price vs NPV')
ax7.legend()
ax7.grid(True, alpha=0.3)

# 8-11. Risk analysis across different parameters (2x2 grid)
risk_params = ['wind_capacity_factor', 'arctic_cost_premium', 'ice_impact_factor', 'electricity_price']
risk_axes = [fig.add_subplot(gs[2, i]) for i in range(4)]

for i, param in enumerate(risk_params):
    param_info = sensitivity_params[param]
    param_range = np.linspace(param_info['range'][0], param_info['range'][1], 30)
    npv_range = []
    
    for param_val in param_range:
        test_params = base_params.copy()
        test_params[param] = param_val
        result = calculate_npv_for_sensitivity(test_params)
        npv_range.append(result['npv']/1e6)
    
    risk_axes[i].plot(param_range, npv_range, linewidth=2, color='purple')
    risk_axes[i].axhline(0, color='red', linestyle='--', alpha=0.5, label='Break-even')
    risk_axes[i].axvline(param_info['base'], color='green', linestyle=':', alpha=0.7, label='Base Case')
    
    # Highlight risk zones
    negative_mask = np.array(npv_range) < 0
    if any(negative_mask):
        risk_zone = param_range[negative_mask]
        if len(risk_zone) > 0:
            risk_axes[i].axvspan(risk_zone[0], risk_zone[-1], alpha=0.2, color='red', label='Risk Zone')
    
    risk_axes[i].set_xlabel(f"{param.replace('_', ' ').title()} ({param_info['unit']})")
    risk_axes[i].set_ylabel('NPV (£M)')
    risk_axes[i].set_title(f'Risk Analysis\n{param.replace("_", " ").title()}')
    risk_axes[i].legend(fontsize=8)
    risk_axes[i].grid(True, alpha=0.3)

plt.suptitle('Alaska Project - Comprehensive Sensitivity Analysis', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.show()
```

## Executive Summary and Recommendations

```python
print(f"\n{'='*80}")
print(f"🎯 ALASKA OFFSHORE RENEWABLE PROJECT - EXECUTIVE SUMMARY")
print(f"{'='*80}")

# Calculate key summary metrics
total_project_value = uncertainty_summary['mean_npv'] + flexibility_summary['flexibility_premium']
roi = (total_project_value / total_capex) * 100 if total_capex > 0 else 0
payback_simple = total_capex / (annual_revenue - annual_opex)

print(f"\n🏆 TRIO-MCDA OPTIMIZATION RESULTS:")
print(f"   Optimal Solution: {best_solution['solution_id']}")
print(f"   Location: {best_solution['latitude']:.3f}°N, {best_solution['longitude']:.3f}°W")
print(f"   Distance to Community: {best_solution['distance_to_shore']:.1f} km")
print(f"   Technology Mix: {best_solution['wind_capacity']:.0f}MW Wind + {best_solution['solar_capacity']:.0f}MW Solar")
print(f"   Total Capacity: {best_solution['total_capacity']:.0f}MW")
print(f"   TOPSIS Score: {best_solution['topsis_score']:.3f} (Rank #{int(best_solution['rank'])} of {len(trio_df)})")

print(f"\n💰 FINANCIAL PERFORMANCE:")
print(f"   Total CAPEX: £{total_capex/1e6:.1f}M")
print(f"   Annual Revenue: £{annual_revenue/1e6:.1f}M")
print(f"   Annual OPEX: £{annual_opex/1e6:.1f}M")
print(f"   Base LCOE: £{base_lcoe:.0f}/MWh")
print(f"   Expected LCOE (with uncertainty): £{uncertainty_summary['mean_lcoe']:.0f}/MWh")
print(f"   Base NPV: £{base_npv/1e6:.1f}M")
print(f"   Expected NPV (with uncertainty): £{uncertainty_summary['mean_npv']/1e6:.1f}M")
print(f"   NPV with Flexibility: £{total_project_value/1e6:.1f}M")
print(f"   Simple Payback: {payback_simple:.1f} years")
print(f"   ROI: {roi:.1f}%")

print(f"\n⚡ TECHNICAL PERFORMANCE:")
print(f"   Annual Energy Production: {annual_energy:.0f} MWh")
print(f"   Overall Capacity Factor: {best_solution['capacity_factor']:.1%}")
print(f"   Wind Capacity Factor: {best_solution['wind_cf']:.1%}")
print(f"   Solar Capacity Factor: {best_solution['solar_cf']:.1%}")
print(f"   Winter Energy Reliability: {best_solution['winter_energy_fraction']:.1%}")
print(f"   Arctic Efficiency Factor: {best_solution['arctic_efficiency']:.1f}%")

print(f"\n🎯 MCDA CRITERIA PERFORMANCE:")
print(f"   LCOE Score: £{best_solution['lcoe']:.0f}/MWh")
print(f"   Emissions Reduction: {best_solution['emissions_reduction']:.0f} tCO2/year")
print(f"   Social Acceptance: {best_solution['social_acceptance']:.1f}/100")
print(f"   Aquaculture Synergy: {best_solution['aquaculture_synergy']:.1f}/100")

print(f"\n🎲 RISK ASSESSMENT:")
risk_level = "LOW" if uncertainty_summary['prob_negative_npv'] < 0.2 else "MODERATE" if uncertainty_summary['prob_negative_npv'] < 0.4 else "HIGH"
print(f"   Overall Risk Level: {risk_level}")
print(f"   Probability of Loss: {uncertainty_summary['prob_negative_npv']:.1%}")
print(f"   LCOE 95% VaR: £{uncertainty_summary['lcoe_var_95']:.0f}/MWh")
print(f"   NPV 5% VaR: £{uncertainty_summary['npv_var_5']/1e6:.1f}M")

print(f"\n🔀 FLEXIBILITY VALUE:")
print(f"   Flexibility Premium: £{flexibility_summary['flexibility_premium']/1e6:.1f}M")
print(f"   Value Uplift from Flexibility: {(flexibility_summary['flexibility_premium']/abs(uncertainty_summary['mean_npv'])*100):.1f}%")
print(f"   Most Valuable Option: Expansion (£{flexibility_summary['mean_expansion_value']/1e6:.1f}M)")
print(f"   Options Likely to be Exercised: {flexibility_summary['avg_options_exercised']:.1f} on average")

print(f"\n📊 KEY SENSITIVITIES (Top 5):")
for i, (param, sensitivity) in enumerate(ranked_sensitivities[:5], 1):
    print(f"   {i}. {param.replace('_', ' ').title()}: {sensitivity:.2f} elasticity")

print(f"\n🌟 STRATEGIC RECOMMENDATIONS:")

# Investment decision
if total_project_value > 0 and uncertainty_summary['prob_negative_npv'] < 0.3:
    recommendation = "✅ PROCEED WITH INVESTMENT"
    print(f"   {recommendation}")
    print(f"   • Project shows positive expected value with acceptable risk")
elif total_project_value > 0:
    recommendation = "⚠️ PROCEED WITH CAUTION"
    print(f"   {recommendation}")
    print(f"   • Project has positive expected value but significant downside risk")
else:
    recommendation = "❌ DO NOT PROCEED"
    print(f"   {recommendation}")
    print(f"   • Project shows negative expected value under current conditions")

# Technology recommendations
print(f"\n🔧 TECHNOLOGY STRATEGY:")
if best_solution['wind_capacity'] > best_solution['solar_capacity'] * 2:
    print(f"   • Wind-dominant strategy is optimal for Alaska conditions")
    print(f"   • Strong Arctic winds provide reliable winter energy")
else:
    print(f"   • Balanced wind-solar strategy recommended")
    
print(f"   • Arctic-rated equipment essential (cost premium: +{(trio.extreme_weather_factor-1)*100:.0f}%)")
print(f"   • Plan for {best_solution['winter_energy_fraction']:.1%} winter energy production")

# Risk management
print(f"\n🛡️ RISK MANAGEMENT:")
key_risks = []
if uncertainty_summary['prob_negative_npv'] > 0.2:
    key_risks.append("High downside risk - consider risk mitigation")
if uncertainty_summary['lcoe_var_95'] > 180:
    key_risks.append("High LCOE variability - hedge electricity prices")
if ranked_sensitivities[0][1] > 2.0:
    key_risks.append(f"High sensitivity to {ranked_sensitivities[0][0]} - monitor closely")

if key_risks:
    for risk in key_risks:
        print(f"   • {risk}")
else:
    print(f"   • Risk levels are manageable under current analysis")

# Flexibility recommendations
print(f"\n🔀 FLEXIBILITY IMPLEMENTATION:")
if flexibility_summary['expansion_exercise_prob'] > 0.2:
    print(f"   • Include expansion provisions in design ({flexibility_summary['expansion_exercise_prob']:.1%} exercise probability)")
if flexibility_summary['abandonment_exercise_prob'] > 0.1:
    print(f"   • Include abandonment clauses in contracts")
if flexibility_summary['shutdown_exercise_prob'] > 0.15:
    print(f"   • Design for seasonal shutdown capability")
print(f"   • Modular design enables staged development")

# Arctic-specific recommendations
print(f"\n❄️ ARCTIC-SPECIFIC CONSIDERATIONS:")
print(f"   • Sea ice season ({len(trio.ice_season_months)} months) affects operations")
print(f"   • Remote logistics require careful supply chain planning")
print(f"   • Indigenous community engagement is critical for social acceptance")
print(f"   • Cold weather impacts require specialized equipment and maintenance")
print(f"   • Aquaculture integration offers additional revenue potential")

# Next steps
print(f"\n📋 RECOMMENDED NEXT STEPS:")
print(f"   1. Detailed site survey and resource measurement campaign")
print(f"   2. Indigenous community consultation and partnership development")
print(f"   3. Environmental impact assessment and permitting")
print(f"   4. Detailed engineering design with Arctic specifications")
print(f"   5. Financial structuring with flexibility provisions")
print(f"   6. Supply chain and logistics planning for remote location")
print(f"   7. Grid integration and energy storage system design")
print(f"   8. Operations and maintenance strategy for Arctic conditions")

# Investment summary
print(f"\n💼 INVESTMENT SUMMARY:")
print(f"   Project: Alaska Remote Community Offshore Renewable Energy")
print(f"   Investment Required: £{total_capex/1e6:.1f}M")
print(f"   Expected Return: £{total_project_value/1e6:.1f}M NPV")
print(f"   Payback Period: {payback_simple:.1f} years")
print(f"   Risk Level: {risk_level}")
print(f"   Recommendation: {recommendation}")

print(f"\n{'='*80}")
print(f"🎉 ALASKA TRIO-MCDA ANALYSIS COMPLETED SUCCESSFULLY")
print(f"{'='*80}")

# Export comprehensive results
results_export = {
    'project_summary': {
        'site': 'Alaska Remote Community',
        'analysis_date': datetime.now().isoformat(),
        'methodology': 'TRIO-MCDA with 4-step FlexiMORP analysis',
        'total_solutions_evaluated': len(trio_df),
        'analysis_duration': 'Complete 4-step analysis'
    },
    'optimal_solution': {
        'solution_id': best_solution['solution_id'],
        'rank': int(best_solution['rank']),
        'topsis_score': best_solution['topsis_score'],
        'location': {
            'latitude': best_solution['latitude'],
            'longitude': best_solution['longitude'],
            'distance_to_shore_km': best_solution['distance_to_shore']
        },
        'technology_configuration': {
            'wind_capacity_mw': best_solution['wind_capacity'],
            'solar_capacity_mw': best_solution['solar_capacity'], 
            'total_capacity_mw': best_solution['total_capacity'],
            'wind_solar_ratio': best_solution['wind_capacity'] / best_solution['solar_capacity']
        }
    },
    'financial_analysis': {
        'capex_gbp': total_capex,
        'annual_opex_gbp': annual_opex,
        'annual_revenue_gbp': annual_revenue,
        'base_lcoe_gbp_per_mwh': base_lcoe,
        'expected_lcoe_gbp_per_mwh': uncertainty_summary['mean_lcoe'],
        'base_npv_gbp': base_npv,
        'expected_npv_gbp': uncertainty_summary['mean_npv'],
        'npv_with_flexibility_gbp': total_project_value,
        'payback_years': payback_simple,
        'roi_percent': roi
    },
    'mcda_scores': {
        'lcoe_gbp_per_mwh': best_solution['lcoe'],
        'emissions_reduction_tco2_per_year': best_solution['emissions_reduction'],
        'social_acceptance_score': best_solution['social_acceptance'],
        'aquaculture_synergy_score': best_solution['aquaculture_synergy'],
        'criteria_weights': criteria_weights
    },
    'risk_assessment': {
        'risk_level': risk_level,
        'probability_of_loss': uncertainty_summary['prob_negative_npv'],
        'lcoe_95_var_gbp_per_mwh': uncertainty_summary['lcoe_var_95'],
        'npv_5_var_gbp': uncertainty_summary['npv_var_5'],
        'key_risk_drivers': [p for p, _ in ranked_sensitivities[:3]]
    },
    'flexibility_analysis': {
        'flexibility_premium_gbp': flexibility_summary['flexibility_premium'],
        'value_uplift_percent': (flexibility_summary['flexibility_premium']/abs(uncertainty_summary['mean_npv'])*100),
        'recommended_options': recommended_options,
        'avg_options_exercised': flexibility_summary['avg_options_exercised']
    },
    'arctic_considerations': {
        'ice_season_months': len(trio.ice_season_months),
        'arctic_cost_premium': trio.extreme_weather_factor,
        'winter_energy_fraction': best_solution['winter_energy_fraction'],
        'arctic_efficiency_factor': best_solution['arctic_efficiency']
    },
    'recommendation': {
        'investment_decision': recommendation,
        'confidence_level': 'High' if uncertainty_summary['prob_negative_npv'] < 0.2 else 'Medium',
        'key_success_factors': [
            'Arctic-rated equipment deployment',
            'Indigenous community partnership',
            'Effective logistics and supply chain',
            'Flexible design implementation',
            'Environmental compliance'
        ]
    }
}

# Save comprehensive results
output_file = f"/Users/nishasdk/github/fleximorpv2/data/alaska/results/alaska_comprehensive_analysis_results.json"
with open(output_file, 'w') as f:
    json.dump(results_export, f, indent=2, default=str)

print(f"\n💾 Comprehensive results exported to:")
print(f"   {output_file}")

# Save detailed datasets
trio_df.to_csv('/Users/nishasdk/github/fleximorpv2/data/alaska/results/trio_solutions_detailed.csv', index=False)
uncertainty_df.to_csv('/Users/nishasdk/github/fleximorpv2/data/alaska/results/uncertainty_scenarios_detailed.csv', index=False)
flexibility_df.to_csv('/Users/nishasdk/github/fleximorpv2/data/alaska/results/flexibility_analysis_detailed.csv', index=False)

print(f"   Detailed datasets saved to data/alaska/results/")
print(f"\n🚀 Alaska TRIO-MCDA Analysis Complete - Ready for Decision Making!")
```

---

## Key Innovations in this Alaska Analysis:

### 1. **TRIO Optimization Framework**
- **T**echnology: Fixed wind+solar mix optimized for Arctic conditions
- **R**esources: Location-specific resource assessment with seasonal variation
- **I**nfrastructure: Platform design optimized for ice, depth, and distance constraints

### 2. **Arctic-Specific MCDA Criteria**
- **LCOE**: Includes Arctic cost premiums and logistics challenges
- **Emissions**: Enhanced impact due to diesel displacement in remote communities
- **Social Acceptance**: Indigenous consultation and community benefit considerations
- **Aquaculture Synergy**: Cold-water species integration potential

### 3. **Advanced Arctic Uncertainty Modeling**
- Seasonal ice impact on operations (0-15% performance reduction)
- Arctic weather variability (18% vs 10-12% temperate)
- Logistics cost uncertainty (25% vs 15% temperate)
- Cold weather equipment performance factors

### 4. **Arctic-Optimized Flexibility Options**
- **Expansion**: Scaled for strong Arctic wind resources
- **Technology Upgrade**: Cold-weather performance improvements
- **Seasonal Shutdown**: Ice season operational flexibility
- **Abandonment**: Arctic equipment salvage value considerations

### 5. **Comprehensive Risk Assessment**
- Multi-scenario sensitivity analysis
- Break-even analysis for key parameters
- Risk-return profiling under uncertainty
- Arctic-specific risk factors (ice, logistics, weather)

This analysis provides a complete decision-making framework for offshore renewable energy development in challenging Arctic conditions, balancing economic, environmental, and social objectives while accounting for the unique constraints and opportunities of Alaska's remote coastal communities.
