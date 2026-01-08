"""
Condition Evaluator
Safely evaluates entry/exit conditions
Supports: >, <, >=, <=, ==, AND, OR
"""
import re
from datetime import datetime
from typing import Any

from logger import setup_logger

logger = setup_logger(__name__)

class ConditionEvaluator:
    """Safely evaluates trading conditions"""
    
    def __init__(self):
        # Allowed operators and functions for safety
        self.safe_dict = {
            '__builtins__': {},
            'abs': abs,
            'max': max,
            'min': min,
        }

    def _normalize_time(self, time_str: str) -> int:
        """Convert HH:MM time string to minutes since midnight"""
        def repl(match):
            h, m= map(int, match.group(1).split(":"))
            return str(h*60 +m)
        return re.sub(r'(\d{1,2}:\d{2})', repl, time_str)
    
    def evaluate(self, condition: str, current_price: float) -> bool:
        """
        Evaluate a condition string safely
        
        Args:
            condition: Condition string like "price > 20100 OR time >= 15:20"
            current_price: Current market price
        
        Returns:
            True if condition is met, False otherwise
        """
        try:
            # Prepare variables
            now = datetime.now()
            variables = {
                'price': current_price,
                'time': now.hour * 60 + now.minute,  # time in minutes since midnight
            }
            
            # Parse and evaluate condition
            result = self._safe_eval(condition, variables)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _safe_eval(self, expression: str, variables: dict) -> Any:
        """
        Safely evaluate expression with given variables
        
        Supports:
        - Comparisons: >, <, >=, <=, ==, !=
        - Logical: AND, OR
        - Variables: price, time
        """
        # Replace logical operators with Python equivalents
        expression = expression.replace(' AND ', ' and ')
        expression = expression.replace(' OR ', ' or ')
        expression = self._normalize_time(expression)
        
        # Build safe evaluation context
        eval_dict = {**self.safe_dict, **variables}
        
        # Validate expression (security check)
        if not self._is_safe_expression(expression):
            raise ValueError(f"Unsafe expression: {expression}")
        
        # Evaluate
        try:
            result = eval(expression, {"__builtins__": {}}, eval_dict)
            return result
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            raise
    
    def _is_safe_expression(self, expression: str) -> bool:
        """
        Check if expression is safe to evaluate
        Only allows: numbers, operators, 'price', 'time', parentheses
        """
        # Remove allowed tokens
        cleaned = expression
        cleaned = re.sub(r'\d+\.?\d*', '', cleaned)  # numbers
        cleaned = re.sub(r'price|time', '', cleaned)  # variables
        cleaned = re.sub(r'[><=!]+', '', cleaned)  # comparison operators
        cleaned = re.sub(r'\s+', '', cleaned)  # whitespace
        cleaned = re.sub(r'and|or', '', cleaned)  # logical operators
        cleaned = re.sub(r'[():]', '', cleaned)  # parentheses and colons
        
        # If anything remains, it's potentially unsafe
        if cleaned:
            logger.warning(f"Potentially unsafe tokens in expression: '{cleaned}'")
            return False
        
        return True