from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.sp_api import get_access_token, check_asin_restriction
from app.services.database import save_result, get_cached_result
from app.auth import get_current_user

router = APIRouter()


class ASINRequest(BaseModel):
    asins: list[str]


@router.post("/check-asin")
def check_asin(request: ASINRequest, current_user: str = Depends(get_current_user)):
    if not request.asins:
        raise HTTPException(status_code=400, detail="Liste d'ASINs vide")

    results = []
    asins_to_check = []

    # Vérifie le cache d'abord
    for asin in request.asins:
        cached = get_cached_result(asin)
        if cached:
            results.append(cached)
        else:
            asins_to_check.append(asin)

    # Appelle SP-API uniquement pour les ASINs non cachés
    if asins_to_check:
        try:
            access_token = get_access_token()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur token LWA : {str(e)}")

        for asin in asins_to_check:
            result = check_asin_restriction(asin, access_token)
            save_result(result["asin"], result["status"], result["reason"])
            results.append(result)

    return {"results": results}