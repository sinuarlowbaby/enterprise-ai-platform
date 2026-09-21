"""
Security and Tenant Isolation Exceptions for Retrieval.

Guards against cross-tenant data leakage by rejecting unauthorized, missing,
or mismatched tenant context queries.
"""


class TenantSecurityError(Exception):
    """Base exception for all tenant boundary and authorization violations."""
    pass


class MissingTenantContextError(TenantSecurityError):
    """Raised when an operation is executed without a mandatory, valid tenant_id."""
    def __init__(self, message: str = "Operation rejected: Missing tenant_id context.") -> None:
        super().__init__(message)


class TenantMismatchError(TenantSecurityError):
    """Raised when the authenticated caller's tenant does not match the target query tenant."""
    def __init__(
        self,
        caller_tenant: str,
        target_tenant: str,
        message: str | None = None,
    ) -> None:
        msg = (
            message
            or f"Unauthorized cross-tenant access attempt: caller tenant '{caller_tenant}' "
            f"does not match requested tenant '{target_tenant}'."
        )
        super().__init__(msg)
        self.caller_tenant = caller_tenant
        self.target_tenant = target_tenant


class InvalidVectorDimensionError(TenantSecurityError):
    """Raised when an input query embedding does not match the configured vector dimensions."""
    def __init__(self, actual_dim: int, expected_dim: int) -> None:
        super().__init__(
            f"Invalid query vector dimension: got {actual_dim}, expected {expected_dim}."
        )
        self.actual_dim = actual_dim
        self.expected_dim = expected_dim
