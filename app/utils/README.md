# Utility Functions Module

## Overview
Helper functions and utilities used across the application.

## Structure

```
utils/
├── logger.py         # Logging configuration
├── validators.py     # Custom validators
├── helpers.py        # General helper functions
├── formatters.py     # Data formatting
└── __init__.py
```

## Logger

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Operation completed", extra={"user_id": user.id})
```

## Validators

```python
from app.utils.validators import validate_email, validate_phone

is_valid = validate_email("user@example.com")
```

## Helpers

```python
from app.utils.helpers import (
    generate_unique_code,
    calculate_business_days,
    sanitize_html
)

code = generate_unique_code()  # "ABC-123"
days = calculate_business_days(start_date, end_date)
```

---

**Related:** [Core](../core/README.md)
