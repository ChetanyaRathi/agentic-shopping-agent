from pydantic import BaseModel, Field


class ExtractedProduct(BaseModel):
    title: str = Field(description="The product name/title")
    price: float | None = Field(default=None, description="Numeric price only, no currency symbol")
    currency: str | None = Field(default=None, description="Currency symbol or code, e.g. £, $, USD")
    color: str | None = Field(default=None, description="Color ONLY if stated in the text, else null")
    in_stock: bool | None = Field(default=None, description="True if available, else false/null")

class Product(ExtractedProduct):
    url: str = Field(description="The product page URL")


class Constraints(BaseModel):
    product: str = Field(description="The product type, e.g. 'backpack'")
    price_min: float | None = Field(default=None, description="Minimum price")
    price_max: float | None = Field(default=None, description="Maximum price")
    color: str | None = Field(default=None, description="Desired color, else null")
    count: int = Field(default=6, description="How many results to return")


class Candidate(BaseModel):
    url: str
    title_hint: str | None = None
    source: str | None = None


class RankedResult(BaseModel):
    product: Product
    score: float


class ExtractedProductsList(BaseModel):
    products: list[ExtractedProduct] = Field(default_factory=list, description="List of products found on the page")


