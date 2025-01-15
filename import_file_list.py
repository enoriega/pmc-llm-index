import re
import csv
from datetime import datetime
import logging
from pathlib import Path
from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlmodel import SQLModel, create_engine
from tqdm import tqdm

from models import Article, Journal, License
logging.basicConfig(level = logging.INFO)
engine = create_engine("sqlite:///database5.db")
citation_pattern = re.compile(r"^((?P<title>.+)\.)?(?P<year> \d+)?(?P<month> [\w\-]+)?(?P<day> \d+)?(?P<note> .+)?;(?P<vol>[:\d\w\s\-/\.]+)?(?P<issue>\(.+\))?(?P<eaccession>( doi)?:.+)?$")

def import_file_list(path:Path) -> None:
	""" Imports a PMC file list into the database """
	with path.open() as f, Session(engine, autocommit=False) as session:
		reader = csv.DictReader(f, delimiter=",")
		articles = []
		licenses = {}
		journals = {}

		for ix, row in tqdm(enumerate(reader), desc="Reading data"):
			
			match = citation_pattern.match(row['Article Citation'])

			if match:
				article = {
					"path":row['File'],
					"pmcid":row['Accession ID'],
					"pmid":row['PMID'],
					"last_updated":datetime.strptime(row['Last Updated (YYYY-MM-DD HH:MM:SS)'], "%Y-%m-%d %H:%M:%S"),
					
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
					article["license_id"] = licenses[license]

				articles.append(article)
			else:
				logging.error(f"Could not process {path.name}, row: {ix+1}, row: {row['Article Citation']}")
				
		logging.info(f"Articles: {len(articles)}, Journals: {len(journals)}, Licenses: {len(licenses)}")
		logging.info(f"Creating licenses")
		session.execute(insert(License), [{"id":v, "name":k} for k, v in licenses.items()])
		logging.info(f"Creating journals")
		session.execute(insert(Journal), [{"id":v, "name":k} for k, v in journals.items()])
		logging.info(f"Creating articles")
		session.execute(insert(Article), articles)

		session.commit()


if __name__ == "__main__":
	SQLModel.metadata.create_all(engine)
	import_file_list(Path("oa_file_list.csv"))
