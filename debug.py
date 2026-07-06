import pytest
import sys
sys.exit(pytest.main(["tests/integration/test_end_to_end.py", "-v", "--tb=long", "-s"]))
