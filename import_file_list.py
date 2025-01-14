import csv
from datetime import datetime
import logging
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from tqdm import tqdm

from models import Article

engine = create_engine("sqlite:///database.db")

def import_file_list(path:Path) -> None:
	""" Imports a PMC file list into the database """
	with path.open() as f, Session(engine, autocommit=False) as session:
		reader = csv.DictReader(f, delimiter=",")
		for ix, row in tqdm(enumerate(reader), desc="Importing data"):
			try:
				article = Article(
					path=row['File'],
					citation=row['Article Citation'],
					pmcid=row['Accession ID'],
					last_updated=datetime.strptime(row['Last Updated (YYYY-MM-DD HH:MM:SS)'], "%Y-%m-%d %H:%M:%S"),
					pmid=row['PMID'],
					license=row['License'],
				)
				session.add(article)
			except:
				logging.error(f"Error importing row {ix}")
			if ix % 1000 == 0:
				session.commit()
		session.commit()

if __name__ == "__main__":
	SQLModel.metadata.create_all(engine)
	import_file_list(Path("oa_file_list.csv"))
