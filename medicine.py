from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    category = Column(String(80))
    unit = Column(String(20))
