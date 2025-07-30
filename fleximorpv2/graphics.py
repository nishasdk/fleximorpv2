        risk_values = [0.1, uncertainty_results.risk_metrics.get('overall_risk', 0.2), 0.15]  # Placeholder
        return_values = npv_values
        
        for i, (risk, ret, label) in enumerate(zip(risk_values, return_values, analysis_types)):
            axes[1, 0].scatter(risk, ret, c=colors[i], s=100, label=label)
            axes[1, 0].annotate(label, (risk, ret), xytext=(5, 5), textcoords='offset points')
        
        axes[1, 0].set_xlabel('Risk Score')
        axes[1, 0].set_ylabel('NPV (£M)')
        axes[1, 0].set_title('Risk vs Return')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Technology mix
        tech_capacities = baseline_results.technology_capacities
        tech_colors = [self.colors.get(tech, '#95A5A6') for tech in tech_capacities.keys()]
        
        axes[1, 1].bar(tech_capacities.keys(), tech_capacities.values(), color=tech_colors)
        axes[1, 1].set_title('Technology Mix (Baseline)')
        axes[1, 1].set_ylabel('Capacity (MW)')
        
        plt.tight_layout()
        return fig


def main():
    """Example usage of graphics engine."""
    # This would typically be called from notebooks or webapp
    pass


if __name__ == "__main__":
    main()
