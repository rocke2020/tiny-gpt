import argparse
import json
import math
import os
import random
import re
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath("."))
from loguru import logger
from utils_comm.io_util import de_accent
from utils_comm.file_util import file_util

data_dir = Path("/mnt/nas1/patent_data/anti-inflammation_peptide")
_pmc_file = data_dir / "parsed_pmc_merged_raw.json"
pmc_file = data_dir / "parsed_pmc_merged.json"
pmc_more_merged_file = data_dir / "parsed_pmc_merged_further.json"
sections = set()
section_pat = re.compile(r"^[\W\d]+|^[IVX]+\.\s+|[\W\d]+$")
sections_file = data_dir / "sections.txt"
word_pat = re.compile(r"[a-zA-Z]{2}")
max_section_length = 60
sections_too_long = defaultdict(set)
sections_too_long_file = data_dir / "sections_too_long.json"

sections_excluded_file = data_dir / "sections_excluded.txt"
sections_excluded_more_file = data_dir / "sections_excluded_further.txt"
sections_excluded_repo_file = 'app/tasks/pmc/analyze_data/sections_excluded_further.txt'


def add_text(section_dict, new_v, section):
    text = section_dict["text"]
    text = de_accent(text)
    if word_pat.search(text):
        new_v[section].append(text)


def merge_sections():
    """Merge sections in paragraph to a dict.

    current input format
    [
        {
            "pmc": "PMC7023394",
            "pmid": "31936124",
            "paragraph": [
                {
                    "section": "1. Introduction",
                    "text": "Peptides, polymers composed of amino acids, are known to possess versatile biological functions such as promoting cell proliferation, migration, inflammation/anti-inflammation, angiogenesis, and melanogenesis [1], which causes numerous physiological procedures in human body [2]. The first synthetic peptide incorporated into skin care products in the late 80s was copper glycine-histidine-lysine (Cu-GHK) generated by Pickard in 1973 [3]. Since then, many short synthetic peptides playing roles in inflammation, extracellular matrix synthesis or pigmentation have been developed. These peptides are used for anti-oxidation, whitening effects, \u201cBotox-like\u201d wrinkle smoothing and collagen stimulation."
                },
    """
    data = file_util.read_json(_pmc_file)
    logger.info(f"len(data): {len(data)}")
    new_data = []

    for item in data:
        for k, v in item.items():
            if k == "paragraph":
                new_v = defaultdict(list)
                former_section = ""
                for i, section_dict in enumerate(v):
                    section = section_dict["section"]
                    section = section_pat.sub("", section)
                    if section:
                        section = de_accent(section)
                        former_section = section
                        add_text(section_dict, new_v, section)
                        if len(section) > max_section_length:
                            sections_too_long[item['pmc']].add(section)
                        else:
                            sections.add(section.lower())
                    else:
                        if i == 0 and former_section == "":
                            former_section = "Introduction"
                        if former_section:
                            add_text(section_dict, new_v, former_section)
                        else:
                            logger.warning(
                                f'{item["pmc"] = } has empty section at the first of paragraph. section text:\n{section_dict["text"][:100]}'
                            )
                    # PMC6155558
                    # if section.startswith('CGRP decreases corneal thickness, scar formation, and endothelial cell loss after injury'):
                    #     logger.info(f'{item["pmc"] = } {section_dict["text"] = }')
                    #     raise Exception
                item[k] = new_v
        new_data.append(item)
    file_util.write_json(new_data, pmc_file)
    with open(sections_file, "w") as f:
        for section in sorted(sections):
            f.write(f"{section}\n")
    file_util.write_json(sections_too_long, sections_too_long_file)
    shutil.copy(sections_excluded_repo_file, sections_excluded_file)

    more_merged_data = []
    for item in data:
        new_item = {}
        for k, v in item.items():
            if k == "paragraph":
                new_v = {}
                for section, texts in v.items():
                    new_v[section] = " ".join(texts)
                new_item[k] = new_v
            else:
                new_item[k] = v
        more_merged_data.append(new_item)
    file_util.write_json(more_merged_data, pmc_more_merged_file)


if __name__ == "__main__":
    merge_sections()
    
    logger.info("end")