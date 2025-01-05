import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def create_jwt_middleware(enable: bool, jwt_secret: str):
    """Create a JWT verification middleware with configurable enable flag and secret.

    Args:
        enable: Whether to enable JWT verification
        jwt_secret: Secret key for JWT verification

    Returns:
        A middleware function that can be used with FastAPI dependencies
    """

    async def verify_jwt(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> bool:
        """Verify JWT token from Authorization header."""
        logger.debug(f"verify_jwt: enable={enable}, credentials={credentials}")
        if not enable:
            return True

        if not credentials:
            raise HTTPException(
                status_code=401, detail="Missing authentication credentials"
            )

        try:
            jwt.decode(credentials.credentials, jwt_secret, algorithms=["HS256"])
            return True
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid authentication token")

    return verify_jwt
