from pydantic import BaseModel
from typing import List

class BlogRecommendation(BaseModel):
    recommendations: List[int]
class BlogRequest(BaseModel):
    blog_id:int

