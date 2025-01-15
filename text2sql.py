import os
from typing import Optional
from sqlalchemy import create_engine, inspect, text
from typer import Typer
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


app = Typer()

@app.command()
def print_schema(connection_string: Optional[str] = None):
	""" Print the schema of the database """
	if not connection_string:
		connection_string = os.getenv("CONNECTION_STRING")
	engine = create_engine(connection_string)
	inspector = inspect(engine)
	for table_name in inspector.get_table_names():
		print(f"Schema for table {table_name}:")
		for column in inspector.get_columns(table_name):
			print(f"  {column['name']} ({column['type']})")
		print()

SYSTEM_PROMPT = """
You are a database engine who contains the following tables and their schemas. 
Your task is to generate the SQL statements necessary that resemble the user's query. You must generate only and only SQL for SQLite. Don't add any preamble or explanation along the SQL statement.

Tables:

Schema for table article:
  id (INTEGER) // Primary key, the numerical id of the article within the database
  path (VARCHAR) // The path of the archive file that contains the files associated to the article
  pmcid (VARCHAR) // PMC identifier, a unique identifier assigned to each article in PMC OA
  pmid (VARCHAR) // PubMed identifier, a unique identifier assigned to each article in PubMed. This identifier is different from the PMC identifier
  last_updated (DATETIME) // Time stamp of the last time the article was updated
  journal_id (INTEGER) // Foreign key to the journal table. Use this key to join to the journal table when you need to retrieve the journal's name
  year (INTEGER)	// Year of the article's publication
  month (VARCHAR) // Month or month range of the article's publication
  day (INTEGER) // Day of the month of the article's publication
  volume (INTEGER) // Volume of the journal in which the article was published
  issue (INTEGER) // Issue of the journal in which the article was published
  eaccession (VARCHAR) // Electronic accession number of the article, This can be the page number, the range of the page numbers, a DOI, or any other identifier
  license_id (INTEGER) // Foreign key to the license table. Use this key to join to the license table when you need to retrieve the license's name
  retracted (BOOLEAN) // Indicates whether the article has been retracted or not

Schema for table journal:
  id (INTEGER) // Primary key, the numerical id of the journal within the database
  commercial (BOOLEAN) // Indicates whether the journal is a commercial journal or not
  name (VARCHAR) // The name of the journal. This is the name that is used to refer to the journal in the article's citation

Schema for table license:
  id (INTEGER) // Primary key, the numerical id of the license within the database
  name (VARCHAR) // The name of the license under which the article is distributed

""".strip()

""" Generate SQL from a user query """
prompt_template = ChatPromptTemplate.from_messages(
	[("system", SYSTEM_PROMPT),
	("user", """User's query in natural language: {query}
				SQL statement:""".strip())]
)

llm = ChatOpenAI(model=os.getenv("MODEL_NAME"), temperature=0)
chain = prompt_template | llm | StrOutputParser()

@app.command()
def generate_sql(query:str) -> None:
	print(chain.invoke({"query": query}))

@app.command()
def generate_execute_sql(query:str, connection_string: Optional[str] = None) -> None:
	sql = chain.invoke({"query": query})
	execute_query(sql, connection_string)

@app.command()
def execute_query(query:str, connection_string: Optional[str] = None) -> None:
	""" Generates a SQL statement from a user query and executes it """
	if not connection_string:
		connection_string = os.getenv("CONNECTION_STRING")
	engine = create_engine(connection_string)
	with engine.connect() as conn:
		result = conn.execute(text(query))
		for row in result:
			print(row)

if __name__ == "__main__":
	app()