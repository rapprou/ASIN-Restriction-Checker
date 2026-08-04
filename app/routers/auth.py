from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import authenticate_user, create_access_token

router = APIRouter(tags=["auth"])


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(form_data.username)
    return {"access_token": token, "token_type": "bearer"}