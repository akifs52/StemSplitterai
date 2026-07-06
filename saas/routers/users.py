from fastapi import APIRouter, Depends

from saas.dependencies import AuthContext, get_current_context
from saas.schemas import MeResponse


router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/me", response_model=MeResponse)
def me(context: AuthContext = Depends(get_current_context)):
    return MeResponse(user=context.user, organization=context.organization)

