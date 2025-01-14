""" SQL Models for PMC OA """

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Article(SQLModel, table=True):
	id:Optional[int] = Field(default=None, primary_key=True)
	path:str
	citation:str
	pmcid:str
	last_updated:datetime
	pmid:str
	license:str



