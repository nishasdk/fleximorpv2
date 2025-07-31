"""
Test runner script for FlexiMORP v2 test suite.
Run with: python -m pytest tests/ -v
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run the complete test suite."""
    
    # Test configuration
    test_args = [
        'tests/',  # Test directory
        '-v',      # Verbose output
        '--tb=short',  # Short traceback format
        '--strict-markers',  # Strict marker checking
        '-x',      # Stop on first failure
        '--durations=10',  # Show 10 slowest tests
    ]
    
    # Add coverage if available
    try:
        import pytest_cov
        test_args.extend(['--cov=fleximorpv2', '--cov-report=term-missing'])
    except ImportError:
        print("pytest-cov not available, running without coverage")
    
    # Run tests
    exit_code = pytest.main(test_args)
    return exit_code


def run_unit_tests():
    """Run only unit tests."""
    return pytest.main(['tests/', '-v', '-m', 'unit'])


def run_integration_tests():
    """Run only integration tests."""
    return pytest.main(['tests/', '-v', '-m', 'integration'])


def run_slow_tests():
    """Run slow tests (like Monte Carlo simulations)."""
    return pytest.main(['tests/', '-v', '-m', 'slow'])


if __name__ == "__main__":
    run_tests()
