from dotenv import load_dotenv
from fastapi import FastAPI

from product_chat import router as product_router
from repair_chat import router as repair_router
from ticket_admin import router as ticket_admin_router

load_dotenv()

app = FastAPI()
app.include_router(repair_router)
app.include_router(product_router)
app.include_router(ticket_admin_router)
