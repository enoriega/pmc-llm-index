import os
import re
import csv
from datetime import datetime
import logging
from pathlib import Path
from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlmodel import SQLModel, create_engine
from tqdm import tqdm
from typer import Typer
from models import Article, Journal, License
logging.basicConfig(level = logging.INFO)

app = Typer()

@app.command()
def import_file_list(path:Path, connection_string:str|None = None) -> None:
	""" Imports a list of PMC file lists into the database """

	citation_pattern = re.compile(r"^((?P<title>.+)\.)?(?P<year> \d+)?(?P<month> [\w\-]+)?(?P<day> \d+)?(?P<note> .+)?;(?P<vol>[:\d\w\s\-/\.]+)?(?P<issue>\(.+\))?(?P<eaccession>( doi)?:.+)?$")

	if not connection_string:
		connection_string = os.getenv("CONNECTION_STRING")

	print(connection_string)
	
	engine = create_engine(connection_string)
	SQLModel.metadata.create_all(engine)
	with Session(engine, autocommit=False) as session:
		
		articles = []
		licenses = {}
		license_type = {}
		journals = {}

		for p in path.glob("*filelist.csv"):
			logging.info(f"Reading {p.name}")
			with p.open("r") as f:
				if p.name.startswith("oa_comm"):
					commercial = True
				elif p.name.startswith("oa_noncomm"):
					commercial = False
				else: 
					commercial = None

				reader = csv.DictReader(f, delimiter=",")

				for ix, row in tqdm(enumerate(reader), desc="Reading data"):
					
					match = citation_pattern.match(row['Article Citation'])

					if match:
						article = {
							"path":row['Article File'],
							"pmcid":row['AccessionID'],
							"pmid":row['PMID'],
							"last_updated":datetime.strptime(row['LastUpdated (YYYY-MM-DD HH:MM:SS)'], "%Y-%m-%d %H:%M:%S"),
							"retracted":row['Retracted'] == "yes"
							
						}

						if title := match.group("title"):
							title = title.strip()
							if title not in journals:
								journals[title] = len(journals)
							article["journal_id"] = journals[title]				

						if year := match.group("year"):
							year = int(year.strip())
							article["year"] = year

						if month := match.group("month"):
							month = month.strip()
							article["month"] = month
						
						if day := match.group("day"):
							day = int(day.strip())
							article["day"] = day

						if vol := match.group("vol"):
							vol = vol.strip()
							article["volume"] = vol

						if issue := match.group("issue"):
							issue = issue.strip().strip("()")
							article["issue"] = issue

						if eaccession := match.group("eaccession"):
							eaccession = eaccession.strip().strip(":")
							article["eaccession"] = eaccession

						if license := row['License']:
							license = license.strip()
							if license not in licenses:
								licenses[license] = len(licenses)
								license_type[license] = commercial
							article["license_id"] = licenses[license]

						articles.append(article)
					else:
						logging.error(f"Could not process {path.name}, row: {ix+1}, row: {row['Article Citation']}")
				
		logging.info(f"Articles: {len(articles)}, Journals: {len(journals)}, Licenses: {len(licenses)}")
		logging.info(f"Creating licenses")
		session.execute(insert(License), [{"id":v, "name":k, "commercial":license_type[k]} for k, v in licenses.items()])
		logging.info(f"Creating journals")
		session.execute(insert(Journal), [{"id":v, "name":k} for k, v in journals.items()])
		logging.info(f"Creating articles")
		session.execute(insert(Article), articles)

		session.commit()


if __name__ == "__main__":
	app()
