from pydantic import BaseModel

class PersonBase(BaseModel):
    name: str

class PersonCreate(PersonBase):
    pass

class PersonRead(PersonBase):
    id: int

    class Config:
        orm_mode = True
