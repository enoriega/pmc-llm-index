import os
from smolagents import CodeAgent, LiteLLMModel, Tool, HfApiModel
# import litellm
# litellm.set_verbose=True
import json
from sqlalchemy import (
    create_engine,
    text,
)

connection_string = os.getenv("CONNECTION_STRING")
engine = create_engine(connection_string)

class Text2SQL(Tool):
	SCHEMA = """""".strip()
	
	name = "text_2_sql"
	description = """ This tool takes a SQL query that can be used to retrieve the relevant data as a string representation of the results. 
	The structure of the database for which the SQL query will conform to is given by the following schema: \n""" + SCHEMA

	inputs = {
		"query":
		{
			"type": "string",
			"description": "A SQL query that will be executed by the database engine. The query must be in SQLite format. You must pass a query that fetches exactly the information you need to make the execution efficient. For example, if you are interested in the year of publictaion, only select the year column. Don't pass the entire row of data. \n" + SCHEMA,
		}
	}
	output_type = "string"

	
	def forward(self, query: str) -> str:
		with engine.connect() as conn:
			result = conn.execute(text(query))
			ret = []
			for row in result:
				ret.append(row._mapping)
			return ret
	
model = HfApiModel("Qwen/Qwen2.5-Coder-32B-Instruct", temperature=0.)
	
agent = CodeAgent(
    tools=[Text2SQL()],
	additional_authorized_imports=[],
    # model=LiteLLMModel(os.getenv("MODEL_NAME"), api_base=os.getenv("OPENAI_API_BASE"), api_key=os.getenv("OPENAI_API_KEY")),
	model=model
)
# print(agent.system_prompt)
# GradioUI(agent).launch()

agent.run("Use a SQL statement that works on SQLite to get the schema of the database, then select a few rows from each table to get a sample of the data and give me a summary of what each table and each column represents in simple english terms. Once you have the schema worked out, use it to tell me the name of the journal with the highest number of articles published in the year 2020 and also from all time. Then, or each of the decades since the inception of the database, use a SQL statement that works on SQLite to compute the average yearly number of papers published, Finally, as your last step, out of all the papers that have a year of publication being set, find the PMCID of the oldest paper published and give me a link to it in pubmed. Return the answers to all the questions that I just asked")
agent.write_inner_memory_from_logs()