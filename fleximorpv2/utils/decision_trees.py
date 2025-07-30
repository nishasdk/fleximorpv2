"""
Decision Trees and Rules for Real Options Analysis

Implements decision rules and decision trees for flexible design strategies
including expansion, contraction, abandonment, and technology switching options.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of real option actions"""
    WAIT = "wait"
    EXPAND = "expand_capacity"
    CONTRACT = "contract_capacity"
    ABANDON = "abandon_project"
    SWITCH_TECHNOLOGY = "switch_technology"
    ADD_TECHNOLOGY = "add_technology"
    REMOVE_TECHNOLOGY = "remove_technology"
    DEFER = "defer_investment"
    ACCELERATE = "accelerate_timeline"


class ConditionType(Enum):
    """Types of decision conditions"""
    NPV_THRESHOLD = "npv_threshold"
    CAPACITY_FACTOR = "capacity_factor"
    ELECTRICITY_PRICE = "electricity_price"
    CUMULATIVE_RETURN = "cumulative_return"
    YEARS_ELAPSED = "years_elapsed"
    TECHNOLOGY_PERFORMANCE = "technology_performance"
    ENVIRONMENTAL_COMPLIANCE = "environmental_compliance"
    STAKEHOLDER_ACCEPTANCE = "stakeholder_acceptance"


@dataclass
class DecisionCondition:
    """Individual decision condition"""
    condition_type: ConditionType
    threshold: float
    operator: str  # '>=', '<=', '>', '<', '=='
    weight: float = 1.0
    description: str = ""
    
    def evaluate(self, state: Dict[str, Any]) -> bool:
        """
        Evaluate if condition is met
        
        Args:
            state: Current system state
            
        Returns:
            True if condition is satisfied
        """
        value = self._get_value_from_state(state)
        
        if self.operator == '>=':
            return value >= self.threshold
        elif self.operator == '<=':
            return value <= self.threshold
        elif self.operator == '>':
            return value > self.threshold
        elif self.operator == '<':
            return value < self.threshold
        elif self.operator == '==':
            return value == self.threshold
        else:
            raise ValueError(f"Unknown operator: {self.operator}")
    
    def _get_value_from_state(self, state: Dict[str, Any]) -> float:
        """Extract relevant value from system state"""
        if self.condition_type == ConditionType.NPV_THRESHOLD:
            return state.get('npv', 0)
        elif self.condition_type == ConditionType.CAPACITY_FACTOR:
            return state.get('capacity_factor', 0)
        elif self.condition_type == ConditionType.ELECTRICITY_PRICE:
            return state.get('electricity_price', 0)
        elif self.condition_type == ConditionType.CUMULATIVE_RETURN:
            return state.get('cumulative_return', 0)
        elif self.condition_type == ConditionType.YEARS_ELAPSED:
            return state.get('years_elapsed', 0)
        elif self.condition_type == ConditionType.TECHNOLOGY_PERFORMANCE:
            return state.get('technology_performance', 0)
        elif self.condition_type == ConditionType.ENVIRONMENTAL_COMPLIANCE:
            return state.get('environmental_score', 0)
        elif self.condition_type == ConditionType.STAKEHOLDER_ACCEPTANCE:
            return state.get('stakeholder_score', 0)
        else:
            return 0


@dataclass
class DecisionRule:
    """Decision rule with conditions and actions"""
    name: str
    conditions: List[DecisionCondition]
    action: ActionType
    action_parameters: Dict[str, Any]
    priority: int = 1
    enabled: bool = True
    min_years_elapsed: int = 0
    max_years_elapsed: int = float('inf')
    description: str = ""
    
    def evaluate(self, state: Dict[str, Any]) -> bool:
        """
        Evaluate if all conditions are met
        
        Args:
            state: Current system state
            
        Returns:
            True if rule should trigger
        """
        if not self.enabled:
            return False
        
        # Check timing constraints
        years = state.get('years_elapsed', 0)
        if years < self.min_years_elapsed or years > self.max_years_elapsed:
            return False
        
        # Evaluate all conditions
        condition_results = [condition.evaluate(state) for condition in self.conditions]
        
        # All conditions must be met (AND logic)
        return all(condition_results)
    
    def get_weighted_score(self, state: Dict[str, Any]) -> float:
        """
        Get weighted score for this rule (for ranking multiple applicable rules)
        
        Args:
            state: Current system state
            
        Returns:
            Weighted score for rule priority
        """
        if not self.evaluate(state):
            return 0
        
        # Calculate weighted condition scores
        total_score = 0
        total_weight = 0
        
        for condition in self.conditions:
            value = condition._get_value_from_state(state)
            # Normalize score based on how much the condition exceeds threshold
            if condition.operator in ['>=', '>']:
                score = max(0, (value - condition.threshold) / condition.threshold)
            else:
                score = max(0, (condition.threshold - value) / condition.threshold)
            
            total_score += score * condition.weight
            total_weight += condition.weight
        
        return (total_score / total_weight) * self.priority if total_weight > 0 else 0


class DecisionTree:
    """
    Decision tree for real options analysis
    """
    
    def __init__(self, rules: List[DecisionRule], name: str = "Decision Tree"):
        """
        Initialize decision tree
        
        Args:
            rules: List of decision rules
            name: Name of the decision tree
        """
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self.name = name
        self.decision_history = []
        
        logger.info(f"Initialized decision tree '{name}' with {len(rules)} rules")
    
    def make_decision(self, state: Dict[str, Any], year: int) -> Dict[str, Any]:
        """
        Make decision based on current state
        
        Args:
            state: Current system state
            year: Current decision year
            
        Returns:
            Decision result with action and parameters
        """
        # Add year to state
        state['years_elapsed'] = year
        
        # Find applicable rules
        applicable_rules = [rule for rule in self.rules if rule.evaluate(state)]
        
        if not applicable_rules:
            decision = {
                'action': ActionType.WAIT,
                'parameters': {},
                'year': year,
                'reason': 'No applicable rules',
                'rule_name': None
            }
        else:
            # Select highest priority rule, or highest scoring if same priority
            if len(applicable_rules) == 1:
                selected_rule = applicable_rules[0]
            else:
                # Multiple rules applicable, select by weighted score
                rule_scores = [(rule, rule.get_weighted_score(state)) for rule in applicable_rules]
                selected_rule = max(rule_scores, key=lambda x: x[1])[0]
            
            decision = {
                'action': selected_rule.action,
                'parameters': selected_rule.action_parameters.copy(),
                'year': year,
                'reason': selected_rule.description,
                'rule_name': selected_rule.name,
                'conditions_met': [
                    {
                        'type': cond.condition_type.value,
                        'threshold': cond.threshold,
                        'actual': cond._get_value_from_state(state),
                        'satisfied': cond.evaluate(state)
                    }
                    for cond in selected_rule.conditions
                ]
            }
        
        # Record decision
        self.decision_history.append(decision.copy())
        
        logger.info(f"Year {year}: Decision - {decision['action'].value} ({decision['reason']})")
        
        return decision
    
    def simulate_decisions(self, 
                          scenarios: List[Dict[str, Any]], 
                          years: List[int]) -> List[Dict[str, Any]]:
        """
        Simulate decisions across multiple years/scenarios
        
        Args:
            scenarios: List of state scenarios for each year
            years: List of decision years
            
        Returns:
            List of decisions for each year
        """
        decisions = []
        
        for i, (scenario, year) in enumerate(zip(scenarios, years)):
            decision = self.make_decision(scenario, year)
            decisions.append(decision)
            
            # Log key metrics
            logger.debug(f"Year {year}: NPV={scenario.get('npv', 0):.0f}, "
                        f"CF={scenario.get('capacity_factor', 0):.2f}, "
                        f"Action={decision['action'].value}")
        
        return decisions
    
    def get_decision_summary(self) -> Dict[str, Any]:
        """
        Get summary of decision history
        
        Returns:
            Summary statistics of decisions made
        """
        if not self.decision_history:
            return {'total_decisions': 0}
        
        action_counts = {}
        for decision in self.decision_history:
            action = decision['action'].value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'total_decisions': len(self.decision_history),
            'action_breakdown': action_counts,
            'first_action_year': self.decision_history[0]['year'],
            'last_action_year': self.decision_history[-1]['year'],
            'most_common_action': max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None
        }
    
    def add_rule(self, rule: DecisionRule):
        """Add new rule to decision tree"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added rule '{rule.name}' to decision tree")
    
    def remove_rule(self, rule_name: str):
        """Remove rule from decision tree"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        logger.info(f"Removed rule '{rule_name}' from decision tree")
    
    def enable_rule(self, rule_name: str, enabled: bool = True):
        """Enable or disable a specific rule"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                logger.info(f"{'Enabled' if enabled else 'Disabled'} rule '{rule_name}'")
                break


class RealOptionsAnalyzer:
    """
    Analyzer for real options strategies using decision trees
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize real options analyzer
        
        Args:
            config: Configuration dictionary with flexibility parameters
        """
        self.config = config
        self.flexibility_config = config.get('flexibility', {})
        self.decision_trees = {}
        
        # Create default decision trees for different strategies
        self._create_default_trees()
        
        logger.info("Initialized Real Options Analyzer")
    
    def _create_default_trees(self):
        """Create default decision trees for common strategies"""
        
        # Expansion strategy tree
        expansion_rules = self._create_expansion_rules()
        self.decision_trees['expansion'] = DecisionTree(expansion_rules, "Capacity Expansion")
        
        # Technology switching tree
        switching_rules = self._create_technology_switching_rules()
        self.decision_trees['technology_switching'] = DecisionTree(switching_rules, "Technology Switching")
        
        # Abandonment tree
        abandonment_rules = self._create_abandonment_rules()
        self.decision_trees['abandonment'] = DecisionTree(abandonment_rules, "Project Abandonment")
        
        # Integrated strategy tree (combines all options)
        integrated_rules = expansion_rules + switching_rules + abandonment_rules
        self.decision_trees['integrated'] = DecisionTree(integrated_rules, "Integrated Strategy")
    
    def _create_expansion_rules(self) -> List[DecisionRule]:
        """Create rules for capacity expansion decisions"""
        rules = []
        
        expansion_options = self.flexibility_config.get('expansion_options', [10, 25, 50])
        
        # High performance expansion rule
        rules.append(DecisionRule(
            name="high_performance_expansion",
            conditions=[
                DecisionCondition(ConditionType.NPV_THRESHOLD, 2000000, '>=', description="NPV > $2M"),
                DecisionCondition(ConditionType.CAPACITY_FACTOR, 0.40, '>=', description="CF > 40%"),
                DecisionCondition(ConditionType.YEARS_ELAPSED, 3, '>=', description="At least 3 years operation")
            ],
            action=ActionType.EXPAND,
            action_parameters={
                'expansion_mw': max(expansion_options),  # Largest expansion
                'investment_trigger': 'high_performance'
            },
            priority=3,
            min_years_elapsed=3,
            description="Expand capacity due to excellent performance"
        ))
        
        # Moderate performance expansion rule
        rules.append(DecisionRule(
            name="moderate_expansion",
            conditions=[
                DecisionCondition(ConditionType.NPV_THRESHOLD, 500000, '>=', description="NPV > $500K"),
                DecisionCondition(ConditionType.CAPACITY_FACTOR, 0.30, '>=', description="CF > 30%"),
                DecisionCondition(ConditionType.YEARS_ELAPSED, 5, '>=', description="At least 5 years operation"),
                DecisionCondition(ConditionType.ELECTRICITY_PRICE, 0.12, '>=', description="Price > $0.12/kWh")
            ],
            action=ActionType.EXPAND,
            action_parameters={
                'expansion_mw': expansion_options[1] if len(expansion_options) > 1 else expansion_options[0],
                'investment_trigger': 'moderate_performance'
            },
            priority=2,
            min_years_elapsed=5,
            description="Moderate expansion based on stable performance"
        ))
        
        # Conservative expansion rule
        rules.append(DecisionRule(
            name="conservative_expansion",
            conditions=[
                DecisionCondition(ConditionType.CUMULATIVE_RETURN, 1.5, '>=', description="150% cumulative return"),
                DecisionCondition(ConditionType.CAPACITY_FACTOR, 0.25, '>=', description="CF > 25%"),
                DecisionCondition(ConditionType.YEARS_ELAPSED, 8, '>=', description="At least 8 years operation")
            ],
            action=ActionType.EXPAND,
            action_parameters={
                'expansion_mw': min(expansion_options),  # Smallest expansion
                'investment_trigger': 'conservative'
            },
            priority=1,
            min_years_elapsed=8,
            description="Small expansion after proven long-term success"
        ))
        
        return rules
    
    def _create_technology_switching_rules(self) -> List[DecisionRule]:
        """Create rules for technology switching decisions"""
        rules = []
        
        if not self.flexibility_config.get('technology_switching', False):
            return rules
        
        # Switch to better performing technology
        rules.append(DecisionRule(
            name="performance_technology_switch",
            conditions=[
                DecisionCondition(ConditionType.TECHNOLOGY_PERFORMANCE, 0.20, '<=', description="Current tech CF < 20%"),
                DecisionCondition(ConditionType.YEARS_ELAPSED, 5, '>=', description="At least 5 years operation"),
                DecisionCondition(ConditionType.NPV_THRESHOLD, -500000, '<=', description="Negative NPV trend")
            ],
            action=ActionType.SWITCH_TECHNOLOGY,
            action_parameters={
                'new_technology': 'best_available',
                'switch_trigger': 'poor_performance'
            },
            priority=2,
            min_years_elapsed=5,
            description="Switch technology due to poor performance"
        ))
        
        # Add complementary technology
        rules.append(DecisionRule(
            name="add_complementary_technology",
            conditions=[
                DecisionCondition(ConditionType.NPV_THRESHOLD, 1000000, '>=', description="NPV > $1M"),
                DecisionCondition(ConditionType.CAPACITY_FACTOR, 0.35, '>=', description="CF > 35%"),
                DecisionCondition(ConditionType.YEARS_ELAPSED, 7, '>=', description="At least 7 years operation")
            ],
            action=ActionType.ADD_TECHNOLOGY,
            action_parameters={
                'additional_technology': 'complementary',
                'capacity_fraction': 0.3  # 30% of existing capacity
            },
            priority=1,
            min_years_elapsed=7,
            description="Add complementary technology to diversify portfolio"
        ))
        
        return rules
    
    def _create_abandonment_rules(self) -> List[DecisionRule]:
        """Create rules for project abandonment decisions"""
        rules = []
        
        if not self.flexibility_config.get('abandonment_option', False):
            return rules
        
        # Early abandonment due to poor performance
        rules.append(DecisionRule(
            name="early_abandonment",
            conditions=[
                DecisionCondition(ConditionType.NPV_THRESHOLD, -2000000, '<=', description="NPV < -$2M"),
                DecisionCondition(ConditionType.CAPACITY_FACTOR, 0.15, '<=', description="CF < 15%"),
                DecisionCondition(ConditionType.YEARS_ELAPSED, 3, '>=', description="At least 3 years operation")
            ],
            action=ActionType.ABANDON,
            action_parameters={
                'abandonment_trigger': 'poor_performance',
                'salvage_value_fraction': 0.4
            },
            priority=3,
            min_years_elapsed=3,
            max_years_elapsed=10,
            description="Abandon project due to consistently poor performance"
        ))
        
        # Late-stage abandonment due to end-of-life
        rules.append(DecisionRule(
            name="end_of_life_abandonment",
            conditions=[
                DecisionCondition(ConditionType.YEARS_ELAPSED, 20, '>=', description="At least 20 years operation"),
                DecisionCondition(ConditionType.NPV_THRESHOLD, 0, '<=', description="NPV trending negative")
            ],
            action=ActionType.ABANDON,
            action_parameters={
                'abandonment_trigger': 'end_of_life',
                'salvage_value_fraction': 0.1
            },
            priority=1,
            min_years_elapsed=20,
            description="Abandon aging project at end of economic life"
        ))
        
        # Regulatory/environmental abandonment
        rules.append(DecisionRule(
            name="regulatory_abandonment",
            conditions=[
                DecisionCondition(ConditionType.ENVIRONMENTAL_COMPLIANCE, 0.3, '<=', description="Environmental score < 30%"),
                DecisionCondition(ConditionType.STAKEHOLDER_ACCEPTANCE, 0.2, '<=', description="Stakeholder acceptance < 20%")
            ],
            action=ActionType.ABANDON,
            action_parameters={
                'abandonment_trigger': 'regulatory_environmental',
                'salvage_value_fraction': 0.2
            },
            priority=2,
            description="Abandon due to regulatory or environmental issues"
        ))
        
        return rules
    
    def analyze_flexibility_value(self, 
                                 base_scenario: Dict[str, Any],
                                 scenarios: List[Dict[str, Any]],
                                 decision_years: List[int]) -> Dict[str, Any]:
        """
        Analyze the value of flexibility using real options
        
        Args:
            base_scenario: Base case without flexibility
            scenarios: List of scenarios with uncertainty
            decision_years: Years when decisions can be made
            
        Returns:
            Analysis results including option values
        """
        results = {
            'base_case': base_scenario,
            'flexibility_strategies': {},
            'option_values': {}
        }
        
        # Run each decision tree strategy
        for strategy_name, tree in self.decision_trees.items():
            strategy_results = []
            
            for scenario in scenarios:
                # Simulate decisions for this scenario
                scenario_states = self._generate_scenario_states(scenario, decision_years)
                decisions = tree.simulate_decisions(scenario_states, decision_years)
                
                # Calculate strategy NPV including option exercises
                strategy_npv = self._calculate_strategy_npv(decisions, scenario_states)
                
                strategy_results.append({
                    'scenario_id': scenario.get('id', 'unknown'),
                    'decisions': decisions,
                    'final_npv': strategy_npv,
                    'decision_summary': tree.get_decision_summary()
                })
            
            results['flexibility_strategies'][strategy_name] = strategy_results
            
            # Calculate option value (difference from base case)
            avg_strategy_npv = np.mean([r['final_npv'] for r in strategy_results])
            base_npv = base_scenario.get('npv', 0)
            option_value = avg_strategy_npv - base_npv
            
            results['option_values'][strategy_name] = {
                'average_npv': avg_strategy_npv,
                'base_npv': base_npv,
                'option_value': option_value,
                'option_value_percentage': (option_value / abs(base_npv)) * 100 if base_npv != 0 else 0
            }
        
        # Identify best strategy
        best_strategy = max(results['option_values'].items(), 
                           key=lambda x: x[1]['option_value'])
        
        results['best_strategy'] = {
            'name': best_strategy[0],
            'option_value': best_strategy[1]['option_value']
        }
        
        logger.info(f"Best flexibility strategy: {best_strategy[0]} "
                   f"(Option value: ${best_strategy[1]['option_value']:,.0f})")
        
        return results
    
    def _generate_scenario_states(self, scenario: Dict[str, Any], years: List[int]) -> List[Dict[str, Any]]:
        """Generate system states for each decision year"""
        states = []
        
        for year in years:
            # Create state for this year based on scenario
            state = scenario.copy()
            state['years_elapsed'] = year
            
            # Add some evolution over time (simplified)
            growth_factor = 1 + (year * 0.02)  # 2% annual growth
            state['npv'] = scenario.get('npv', 0) * growth_factor
            
            # Add some variability
            cf_variation = np.random.normal(0, 0.05)  # 5% standard deviation
            state['capacity_factor'] = max(0, scenario.get('capacity_factor', 0.3) + cf_variation)
            
            states.append(state)
        
        return states
    
    def _calculate_strategy_npv(self, decisions: List[Dict[str, Any]], states: List[Dict[str, Any]]) -> float:
        """Calculate NPV including the impact of real option exercises"""
        # Simplified calculation - in practice would be more sophisticated
        base_npv = states[-1].get('npv', 0) if states else 0
        
        # Add value from expansion decisions
        expansion_value = 0
        for decision in decisions:
            if decision['action'] == ActionType.EXPAND:
                expansion_mw = decision['parameters'].get('expansion_mw', 0)
                expansion_value += expansion_mw * 50000  # $50k per MW value
            elif decision['action'] == ActionType.ABANDON:
                salvage_fraction = decision['parameters'].get('salvage_value_fraction', 0)
                expansion_value += base_npv * salvage_fraction - base_npv  # Salvage minus remaining investment
        
        return base_npv + expansion_value
    
    def get_strategy_comparison(self) -> pd.DataFrame:
        """
        Get comparison of different flexibility strategies
        
        Returns:
            DataFrame comparing strategies
        """
        if not hasattr(self, '_last_analysis_results'):
            return pd.DataFrame()
        
        results = self._last_analysis_results
        
        comparison_data = []
        for strategy_name, option_data in results.get('option_values', {}).items():
            comparison_data.append({
                'Strategy': strategy_name,
                'Average NPV': option_data['average_npv'],
                'Base NPV': option_data['base_npv'],
                'Option Value': option_data['option_value'],
                'Option Value %': option_data['option_value_percentage']
            })
        
        return pd.DataFrame(comparison_data).sort_values('Option Value', ascending=False)
