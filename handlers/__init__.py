from aiogram import Router
from handlers.start import router as start_router
from handlers.instagram import router as instagram_router

router = Router()
router.include_router(start_router)
router.include_router(instagram_router)

__all__ = ["router"]
