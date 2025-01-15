""" SQL Models for PMC OA """

from typing import Optional
from sqlmodel import SQLModel, Field, ForeignKey
from datetime import datetime

class Article(SQLModel, table=True):
	id:Optional[int] = Field(default=None, primary_key=True)
	path:str
	pmcid:str
	pmid:str
	last_updated:datetime
	# Publication information
	journal_id:Optional[int] = Field(foreign_key="journal.id")
	year:Optional[int]
	month:Optional[str]
	day:Optional[int]
	volume:Optional[int]
	issue:Optional[int]
	eaccession:Optional[str]
	license_id:int | None = Field(foreign_key="license.id")

class License(SQLModel, table=True):
	id:Optional[int] = Field(default=None, primary_key=True)
	name:str

class Journal(SQLModel, table=True):
	id:Optional[int] = Field(default=None, primary_key=True)
	commercial:bool = Field(default=False)
	name:str