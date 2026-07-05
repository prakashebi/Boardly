from fastapi import APIRouter

from app.api.v1 import attachments, auth, entities, events, members, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(entities.router)
api_router.include_router(attachments.router)
api_router.include_router(events.router)
api_router.include_router(members.router)
