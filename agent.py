import os
from smolagents import CodeAgent, Tool, HfApiModel, ToolCallingAgent, GradioUI, LiteLLMModel
import json
from sqlalchemy import (
	create_engine,
	text,
)
from typer import Typer

import litellm
litellm.set_verbose=True

app = Typer()

class Text2SQL(Tool):
	SCHEMA = """Tables:

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
	
	name = "text_2_sql"
	description = """ This tool takes a SQL query that can be used to retrieve the relevant data as a string representation of the results. The query should be concise and efficient. Do your best to pass an efficient query that fetches only the information you need.
	"""

	inputs = {
		"query":
		{
			"type": "string",
			"description": "A SQL query that will be executed by the database engine. The query must be in SQLite format. You must pass a query that fetches exactly the information you need to make the execution efficient. For example, if you are interested in the year of publictaion, only select the year column. Don't pass the entire row of data. \nThe schema of the database is:\n" ,
		}
	}
	output_type = "string"

	def __init__(self, connection_string: str):
		super().__init__()
		self.engine = create_engine(connection_string)

	def forward(self, query: str) -> str:
		with self.engine.connect() as conn:
			result = conn.execute(text(query))
			ret = []
			for row in result:
				ret.append(row._mapping)
			return ret


def spin_agent(model: str, type: str, connection_string: str,
				num_steps: int = 15, temperature: float = 0.):
	"""
	Spins up an agent with the specified model, type, and connection string.

	Args:
		model (str): The model to be used by the agent.
		type (str): The type of the agent.
		connection_string (str): The connection string for the agent.
		num_steps (int, optional): The number of steps for the agent. Defaults to 15.
		temperature (float, optional): The temperature for the agent. Defaults to 0.

	Returns:
		Agent: The agent with the specified model, type, and connection string.
	"""

	# model = HfApiModel(model, temperature)
	model = LiteLLMModel("openai/Qwen/Qwen2.5-Coder-32B-Instruct", api_base="https://localhost:8000/v1", temperature=temperature)
	
	match type:
		case "tool_calling":
			agent = ToolCallingAgent(
				max_steps=5,
				tools=[Text2SQL(connection_string)],
				model=model
			)
		case "code":
			agent = CodeAgent(
				max_steps=15,
				tools=[Text2SQL(connection_string)],
				model=model
			)

	return agent

@app.command()
def gradio(type_: str = "code"):
	"""
	Spins up a gradio interface for the agent.

	Args:
		type_ : The type of the agent. Either ToolCalling or Code.
	"""

	connection_string = os.getenv("CONNECTION_STRING")
	agent = spin_agent("Qwen/Qwen2.5-Coder-32B-Instruct", type_, connection_string)
	GradioUI(agent).launch()


# agent.run("Use a SQL statement that works on SQLite to get the schema of the database, then select a few rows from each table to get a sample of the data and give me a summary of what each table and each column represents in simple english terms. Once you have the schema worked out, use it to tell me the name of the journal with the highest number of articles published in the year 2020 and also from all time. Then, or each of the decades since the inception of the database, use a SQL statement that works on SQLite to compute the average yearly number of papers published, Finally, as your last step, out of all the papers that have a year of publication being set, find the PMCID of the oldest paper published and give me a link to it in pubmed. Return the answers to all the questions that I just asked")
# agent.run("Now tell me what is the date with year, month and day of the oldest publictaion in the journal with the highest number or articles")
# print(json.dumps(agent.write_inner_memory_from_logs(), indent=2))

if __name__ == "__main__":
	app()