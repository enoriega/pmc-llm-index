import os
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import create_engine, text
# import warnings
# warnings.filterwarnings("ignore", category=UserWarning)

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

llm = ChatOpenAI(model=os.getenv("MODEL_NAME"), temperature=0, api_key="sk-dTIA-a9guZoeCI1KluOD6Q")
chain = prompt_template | llm | StrOutputParser()


connection_string = os.getenv("CONNECTION_STRING")
engine = create_engine(connection_string)


@tool
def generate_sql(query:str) -> str:
    """Generates a SQL statement that matches a query described by the user."""
    return chain.invoke({"query": query})

@tool
def execute_sql(query:str) -> str:
    """Executes a SQL statement and returns the resulting value or table."""
    ret = []
    with engine.connect() as conn:
        result = conn.execute(text(query))
        for row in result:
            ret.append(list(row))
    return ret



tools = [generate_sql, execute_sql]

llm = ChatOpenAI(model="llama3.2:latest", base_url="http://localhost:11434/v1", temperature=0)
llm_with_tools = llm.bind_tools(tools)
# llm_with_tools = llm



query = "Histogram of number of publications per year"

messages = [
    SystemMessage("""You are an AI assistant that reasons over questions about a database.
                   You don't generate SQL text by yourself, instead  you have two tools available: one that generates SQL from a user query and another that executes SQL statements.
                   To answer a question, you will need to call these tools in sequence.
                  
                  Tools:
                    - Name: generate_sql
                      - Description: Generates a SQL statement that matches a query described by the user.
                      - Arguments: question
                          - Descriptuion: The user's query in natural language.
                  
                    - Name: execute_sql
                      - Description: Executes a SQL statement and returns the resulting value or table.
                      - Arguments: query
                          - Description: The SQL statement to execute
                  
                  Examples:
                  User question: Tell me the number of articles published in 2023
                  Call: execute_sql(generate_sql("Tell me the number of articles published in 2023"))
                  Then use the result to elaborate your response

                  
                  """.strip()),
    HumanMessage(query)
]


ai_msg = llm_with_tools.invoke(messages)
while ai_msg.tool_calls:

  messages.append(ai_msg)

  for tool_call in ai_msg.tool_calls:
      selected_tool = {"generate_sql": generate_sql, "execute_sql": execute_sql}[tool_call["name"].lower()]
      tool_msg = selected_tool.invoke(tool_call)
      messages.append(repr(tool_msg))

  ai_msg = llm_with_tools.invoke(messages)


for message in messages:
    print(message)
    print()

# print(llm_with_tools.invoke(messages).content)
