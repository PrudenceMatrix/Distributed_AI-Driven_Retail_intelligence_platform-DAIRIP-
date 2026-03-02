from fastapi import HTTPException, status


class DAIRIPException(Exception):
    """Base exception for all DAIRIP domain errors."""
    pass


class ConcurrencyConflictError(DAIRIPException):
    """Raised when optimistic concurrency control detects a version mismatch."""
    pass


class InsufficientStockError(DAIRIPException):
    """Raised when a sale or reservation exceeds available inventory."""
    pass


class ProductNotFoundError(DAIRIPException):
    """Raised when a product lookup fails."""
    pass


class DuplicateTransactionError(DAIRIPException):
    """Raised when an idempotency key has already been processed."""
    pass


class UnauthorizedBranchError(DAIRIPException):
    """Raised when a user attempts to operate on a branch they don't belong to."""
    pass


# ── HTTP exception helpers ────────────────────────────────────────────────────

def raise_404(detail: str = "Resource not found"):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def raise_409(detail: str = "Conflict"):
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def raise_422(detail: str = "Unprocessable entity"):
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def raise_403(detail: str = "Forbidden"):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)