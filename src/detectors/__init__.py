"""Code detectors for identifying smells, risks, and anti-patterns.

Detectors perform deeper analysis to identify code smells, security risks,
and anti-patterns that go beyond simple rule checks.
"""

from src.detectors.code_smells import detect as detect_code_smells
from src.detectors.security_risks import detect as detect_security_risks
from src.detectors.anti_patterns import detect as detect_anti_patterns

__all__ = [
    "detect_code_smells",
    "detect_security_risks",
    "detect_anti_patterns",
]
