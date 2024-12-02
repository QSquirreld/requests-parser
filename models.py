from pydantic import BaseModel
from typing import Optional, List


class Price(BaseModel):
    basic: Optional[int] = None
    total: Optional[int] = None


class Size(BaseModel):
    price: Optional[Price] = None


class Product(BaseModel):
    id: int
    brand: str
    brandId: int
    name: str
    supplier: str
    supplierId: int
    sizes: List[Size]


class ItemList(BaseModel):
    products: List[Product]


class metaList(BaseModel):
    name: str


class BigData(BaseModel):
    data: ItemList
    metadata: Optional[metaList] = None
