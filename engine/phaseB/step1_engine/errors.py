class InputContractError(ValueError):
    """Raised at input boundaries when an array/state violates the registered contract (technical invalid). Callers convert to technical_fail states."""
