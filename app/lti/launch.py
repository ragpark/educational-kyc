from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/lti")

@router.post("/launch")
async def lti_launch(request: Request):
    """Handle LTI launch requests

    The original implementation referenced an undefined variable
    `state_val` when validating the request. This caused a
    ``NameError`` at runtime. The handler now correctly uses the
    `state` value supplied in the incoming form data.
    """
    form = await request.form()
    id_token = form.get("id_token")
    state = form.get("state")

    if not id_token or not state:
        raise HTTPException(status_code=400, detail="Missing id_token or state parameter")

    # Placeholder for further LTI processing
    return {"status": "success"}
