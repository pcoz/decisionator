# decisionator.py
# Copyright (c) 2025 Edward Chalk (edward@fleetingswallow.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Attribution: This software may be used for commercial and non-commercial
# purposes, provided that credit is given to the original author:
# Edward Chalk (edward@fleetingswallow.com)
#
# Transactional Analysis Multiple Decision-Making Models Integrator
#
# Implementation with OpenAI API and workflow controller

#!/usr/bin/env python3
import os
import json
import openai
import sys
import re
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field

from enum import Enum
import numpy as np

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

import logging
import datetime

####################################################################################################
# Helper functions for Markdown and Word document operations
####################################################################################################
def add_markdown_to_doc(doc, markdown_text):
    '''
    Converts Markdown text into formatted Word document content.
    Handles code blocks, headings, bolding, and regular paragraphs.
    Used for adding summaries and explanations with preserved formatting.
    '''
    lines = re.sub(r'\n\s*\n+', '\n', markdown_text.strip()).split('\n')
    in_code_block = False
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            run = doc.add_paragraph().add_run(line)
            run.font.name = 'Courier New'
            run.font.size = Pt(10)
        else:
            # Handle basic markdown heading
            if line.startswith('### '):
                doc.add_heading(line[4:], level=4)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=3)
            elif line.startswith('# '):
                doc.add_heading(line[2:], level=2)
            elif '**' in line:
                p = doc.add_paragraph()
                parts = line.split('**')
                for j, part in enumerate(parts):
                    if j % 2 == 1:
                        p.add_run(part).bold = True
                    else:
                        p.add_run(part)
            else:
                doc.add_paragraph(line)

def is_markdown(text):
    '''
    Detects if the supplied text includes Markdown formatting cues.
    Returns True if so, else False.
    '''
    return any(s in text for s in ('# ', '## ', '### ', '**', '`', '* '))

class DocAssembler:
    '''
    Utility class for building up a Word document section by section.
    Supports headings, paragraphs, tables, page breaks, and saving.
    Used throughout to build the final decision report.
    '''
    def __init__(self, title="AI Decision-Making Report"):
        self.doc = Document()
        self.section = "main"
        self.doc.add_heading(title, 0)
        self.doc.add_paragraph("Generated using TA Models and OpenAI.")
        self.doc.add_paragraph()
    
    def set_section(self, section_name):
        self.section = section_name
    
    def add_heading(self, text, level=1):
        self.doc.add_heading(text, level=level)
    
    def add_paragraph(self, text, style=None):
        self.doc.add_paragraph(text, style=style)
    
    def add_markdown(self, markdown_text):
        self._add_markdown_to_doc(markdown_text)
    
    def add_table(self, rows, cols):
        return self.doc.add_table(rows=rows, cols=cols)
    
    def add_page_break(self):
        self.doc.add_page_break()
    
    def save(self, filename):
        self.doc.save(filename)
    
    def get_doc(self):
        return self.doc

    def _add_markdown_to_doc(self, markdown_text):
        # This is a direct move of your original function, but using self.doc
        lines = re.sub(r'\n\s*\n+', '\n', markdown_text.strip()).split('\n')
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                run = self.doc.add_paragraph().add_run(line)
                run.font.name = 'Courier New'
                run.font.size = Pt(10)
            else:
                if line.startswith('### '):
                    self.doc.add_heading(line[4:], level=4)
                elif line.startswith('## '):
                    self.doc.add_heading(line[3:], level=3)
                elif line.startswith('# '):
                    self.doc.add_heading(line[2:], level=2)
                elif '**' in line:
                    p = self.doc.add_paragraph()
                    parts = line.split('**')
                    for j, part in enumerate(parts):
                        if j % 2 == 1:
                            p.add_run(part).bold = True
                        else:
                            p.add_run(part)
                else:
                    self.doc.add_paragraph(line)

from docx.shared import Pt, RGBColor, Inches
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def style_table(table):
    '''
    Applies table formatting for Word output.
    Adds black borders to all cells and highlights header row.
    '''
    # 1. Apply black border to all cells
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = tcPr.find(qn('w:tcBorders'))
            if tcBorders is not None:
                tcPr.remove(tcBorders)
            borders_xml = (
                '<w:tcBorders %s>'
                '  <w:top w:val="single" w:sz="6" w:color="000000"/>'
                '  <w:left w:val="single" w:sz="6" w:color="000000"/>'
                '  <w:bottom w:val="single" w:sz="6" w:color="000000"/>'
                '  <w:right w:val="single" w:sz="6" w:color="000000"/>'
                '</w:tcBorders>' % nsdecls('w')
            )
            tcPr.append(parse_xml(borders_xml))
    # 2. Shade top row light grey & bold text
    hdr_cells = table.rows[0].cells
    for cell in hdr_cells:
        cell_paragraph = cell.paragraphs[0]
        for run in cell_paragraph.runs:
            run.font.bold = True
        # Light grey shading (RGB #D9D9D9)
        cell._tc.get_or_add_tcPr().append(
            parse_xml(r'<w:shd {} w:fill="D9D9D9"/>'.format(nsdecls('w')))
        )
    # 3. Set column widths (minimum for headings & score columns)
    # WARNING: Word often ignores explicit widths, but setting helps.
    if len(hdr_cells) == 3:
        hdr_cells[0].width = Inches(4.0)  # Main consideration text, wider
        hdr_cells[1].width = Inches(1.1)  # Positive/Negative, narrow
        hdr_cells[2].width = Inches(0.7)  # Score, narrow

def get_heatmap_color(score, min_neg, max_pos, orientation):
    '''
    Maps a numerical score and orientation to a color for table cell shading.
    Used to visually distinguish positive and negative considerations.
    '''
    # Handle None and convert to float
    try:
        s = float(score)
    except Exception:
        return None
    # Negatives
    if orientation == "negative" and min_neg < 0 and s < 0:
        t = abs(s) / abs(min_neg) if min_neg != 0 else 0
        # Interpolate R: 251→255, G: 234→0, B: 234→0
        r = int(251 + (255-251)*t)  # almost no change
        g = int(234 - 234*t)        # 234→0
        b = int(234 - 234*t)        # 234→0
        return f"{r:02x}{g:02x}{b:02x}"
    # Positives
    if orientation == "positive" and max_pos > 0 and s > 0:
        t = s / max_pos if max_pos != 0 else 0
        # Interpolate R: 245→0, G: 255→204, B: 245→0
        r = int(245 - 245*t)       # 245→0
        g = int(255 - (255-204)*t) # 255→204
        b = int(245 - 245*t)       # 245→0
        return f"{r:02x}{g:02x}{b:02x}"
    # Zero or unrecognized: no shade
    return None

def normalized_score(cons):
    '''
    Returns a normalized (possibly negated) score for a consideration,
    so negative-oriented fields always appear as negative numbers.
    '''
    try:
        val = float(cons.score)
    except Exception:
        val = 0.0
    # If it's supposed to be negative but is positive, flip it
    if cons.orientation == "negative" and val > 0:
        return -val
    return val

# Sorting utility: sorts by score, then text alphabetically (case-insensitive)
def sort_considerations(conslist, negative=True):
    '''
    Sorts a list of Consideration objects.
    For negatives, sorts from most to least negative; for positives, ascending order.
    '''
    return sorted(
        conslist,
        key=lambda x: (float(x.score), str(x.text).lower())
    ) if negative else sorted(
        conslist,
        key=lambda x: (float(x.score), str(x.text).lower())
    )
    
from difflib import SequenceMatcher

def dedupe_considerations(conslist, similarity_cutoff=0.92):
    '''
    Deduplicate a list of Consideration objects, both by exact text and near-match (fuzzy).
    - similarity_cutoff: float between 0 and 1.0; higher = stricter.
    Returns a list with duplicates removed.
    '''
    seen = set()
    deduped = []
    texts = []
    for c in conslist:
        text = str(c.text).strip()
        # Exact dedupe
        if text.lower() in seen:
            continue
        # Fuzzy dedupe against previous
        is_dupe = False
        for prev in texts:
            if SequenceMatcher(None, text.lower(), prev.lower()).ratio() >= similarity_cutoff:
                is_dupe = True
                break
        if not is_dupe:
            deduped.append(c)
            texts.append(text)
            seen.add(text.lower())
    return deduped

def signed_score(orientation, score):
    '''
    Ensures negative considerations have negative scores and positive ones have positive.
    Used to enforce orientation-appropriate sign in all tables.
    '''
    try:
        val = float(score)
    except Exception:
        val = 0.0
    if orientation == "negative" and val > 0:
        return -val
    if orientation == "positive" and val < 0:
        return abs(val)
    return val

####################################################################################################
# Logging and API Config
####################################################################################################
# Set up logging to file for API responses and debug info.
LOG_FILENAME = "ta_api_calls.log"
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode='a',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)


def log_api_data(label: str, data: Any):
    '''
    Logs data to a log file with a label and ensures it is stringified.
    '''
    try:
        if isinstance(data, (dict, list)):
            text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            text = str(data)
        logging.info(f"[{label}] {text}")
    except Exception as e:
        logging.error(
            f"[{label}] (Logging Error) {e} // Original data: {data}")


# Read OpenAI API key from environment and configure API client.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")
openai.api_key = OPENAI_API_KEY

####################################################################################################
# Data field mapping and utility functions
####################################################################################################

# Dictionaries for mapping LLM numeric output fields to semantic labels.

EGO_FIELDS_BY_ID = {
    "ego_state": "ego_state",  # Name
    "1": "concerns",
    "2": "hopes",
    "3": "fears",
    "4": "score",
    "5": "reasoning"
}
SUBEGO_FIELDS_BY_ID = {
    "sub_state": "sub_state",
    "core_function": "core_function",
    "1": "concerns",
    "2": "stance",
    "3": "non_negotiables",
    "4": "reasoning"
}
MATRIX_FIELDS_BY_ID = {
    "ego_state": "ego_state",
    "maslow_level": "maslow_level",
    "1": "score",
    "2": "reasoning"
}

# Maps for field_id
FIELD_ID_TO_LABEL = {
    "1": "concern",
    "2": "hope",
    "3": "fear",
    "4": "score",  # not usually needed as consideration
    "5": "reasoning",  # will filter OUT for tables!
}
FIELD_ID_TO_ORIENTATION = {
    "1": "negative",   # Concerns
    "2": "positive",   # Hopes
    "3": "negative",   # Fears
    "4": "neutral",    # Scores, rarely needed as a consideration
    "5": "neutral",    # Reasoning – you’ll filter these out for tables!
}


@dataclass
class EgoStateResponse:
    '''
    Data container for storing results of an ego state analysis in Model 1.
    '''
    ego_state: str
    concerns: List[str]
    hopes: List[str]
    fears: List[str]
    score: float
    reasoning: str


@dataclass
class SubEgoStateResponse:
    '''
    Data container for results from a sub-ego state analysis in Model 2.
    '''
    sub_state: str
    core_function: str
    concerns: List[str]
    stance: int  # -2 to +2
    non_negotiables: List[str]
    reasoning: str


@dataclass
class MatrixCell:
    '''
    Stores a single (ego_state, maslow_level) cell from Model 3’s matrix.
    '''
    ego_state: str
    maslow_level: str
    score: float
    reasoning: str


@dataclass
class DecisionResult:
    '''
    Stores the main output/result from any of the three decision models.
    '''
    model_used: str
    recommendation: str
    confidence_score: float
    conditions: List[str]
    reasoning: str
    detailed_analysis: Dict[str, Any]
    
@dataclass
class Consideration:
    '''
    Represents a single consideration (pro/con/requirement/score)
    as output by a decision model, with metadata for sorting/grouping.
    '''
    text: str
    source_model: str
    source_context: str
    orientation: str  # 'positive', 'negative', or 'neutral'
    option: str = None
    score: float = None
    extra: dict = field(default_factory=dict)
    field_id: str = None  # <-- Add this line!

def extract_numeric(val):
    '''
    Extracts a float from a string (or int/float), using only 0-9 and '.' characters.
    If conversion fails, returns 0.0.
    '''
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return 0.0
    digits = ''.join([c for c in val if (c.isdigit() or c == '.')])
    try:
        return float(digits) if digits else 0.0
    except Exception:
        return 0.0


def map_fields_by_id(data: dict, id_map: dict, dataclass_type):
    '''Convert LLM output (with numeric keys) to dataclass fields and handle type coercion.'''
    mapped = {}
    for id_key, attr in id_map.items():
        if id_key in data:
            mapped[attr] = data[id_key]
    # Type coercion for each field
    for f in dataclass_type.__dataclass_fields__:
        typ = dataclass_type.__dataclass_fields__[f].type
        if f in mapped:
            if typ == float:
                mapped[f] = extract_numeric(mapped[f])
            elif typ == int:
                mapped[f] = int(extract_numeric(mapped[f]))
            elif typ == list or typ == List[str]:
                v = mapped[f]
                if isinstance(v, str):
                    try:
                        mapped[f] = json.loads(v)
                    except Exception:
                        mapped[f] = [s.strip() for s in v.split(",")]
                elif not isinstance(v, list):
                    mapped[f] = [v]
    # If a required field is missing, fill with defaults
    for f in dataclass_type.__dataclass_fields__:
        typ = dataclass_type.__dataclass_fields__[f].type
        if f not in mapped:
            if typ == float:
                mapped[f] = 0.0
            elif typ == int: mapped[f] = 0
            elif typ == list or typ == List[str]:
                mapped[f] = []
            else: mapped[f] = ""
    return dataclass_type(**mapped)

####################################################################################################
# Core Enums and Controller Classes
####################################################################################################

class DecisionModel(Enum):
    '''
    Enum of supported Transactional Analysis decision models.
    Used to select which workflow to run.
    '''
    DEMOCRATIC_COUNCIL = "model1"
    SECOND_ORDER_NEGOTIATIONS = "model2"
    MASLOW_TA_MATRIX = "model3"


class WorkflowController:
    '''
    Orchestrates all operations for the three supported decision models.
    Handles prompt creation, OpenAI API calls, model execution, and parsing.
    Provides public methods for running each model and extracting options.
    '''

    def __init__(self):
        self.workflows = {
            DecisionModel.DEMOCRATIC_COUNCIL: {
                "steps": [
                    "independent_ego_analysis",
                    "council_synthesis",
                    "final_decision"
                ],
                "ego_states": ["Parent", "Adult", "Child"]
            },
            DecisionModel.SECOND_ORDER_NEGOTIATIONS: {
                "steps": [
                    "sub_ego_analysis",
                    "cluster_dialogues",
                    "cross_cluster_negotiation",
                    "weighted_vote"
                ],
                "sub_ego_states": [
                    "Parent-in-Parent", "Adult-in-Parent", "Child-in-Parent",
                    "Parent-in-Adult", "Adult-in-Adult", "Child-in-Adult",
                    "Parent-in-Child", "Adult-in-Child", "Child-in-Child"
                ]
            },
            DecisionModel.MASLOW_TA_MATRIX: {
                "steps": [
                    "matrix_evaluation",
                    "tier_by_tier_check",
                    "mitigation_planning",
                    "utility_calculation"
                ],
                "ego_states": ["Parent", "Adult", "Child"],
                "maslow_levels": ["Physiological", "Safety", "Love/Belonging", "Esteem", "Self-Actualization"]
            }
        }

    def extract_options(self, problem: str) -> list:
        prompt = f'''
    Given the following decision problem, enumerate the main mutually-exclusive options under consideration, in clear, concise terms.
    Return as JSON with unique short IDs and one-line descriptions.
    
    Problem:
    {problem}
    
    Example:
    {{
      "options": [
        {{"id": "A", "text": "Fish in the safe zone"}},
        {{"id": "B", "text": "Fish in the disputed zone"}},
        {{"id": "C", "text": "Repair the boat before going out"}}
      ]
    }}
    '''
        response = self._call_openai_api(prompt)
        data = self._handle_json_parse(response)
        return data.get("options", [])
    
    def _make_final_decision_model1(self, problem: str, ego_responses: List[EgoStateResponse], synthesis: Dict[str, Any]) -> DecisionResult:
        '''Make the final decision for Model 1'''
        avg_score = np.mean([response.score for response in ego_responses])
        # On -10 to +10 scale: Accept for positive, Reject for negative
        recommendation = "Accept" if avg_score >= 0 else "Reject"
        if synthesis["consensus_level"] < 3:
            recommendation += " (with reservations)"
        conditions = synthesis.get("mitigation_plans", [])
        return DecisionResult(
            model_used="Model 1: Democratic Ego State Council",
            recommendation=recommendation,
            confidence_score=float(avg_score),
            conditions=conditions,
            reasoning=synthesis["synthesis_reasoning"],
            detailed_analysis={
                "ego_responses": [asdict(r) for r in ego_responses],
                "synthesis": synthesis,
                "average_score": avg_score
            }
        )
    
    def _conduct_weighted_vote_model2(self, problem: str, negotiation_results: Dict[str, Any]) -> DecisionResult:
        '''
        Conduct the final weighted vote for Model 2 (with stances in -10 to +10 range).
        '''
        # Define weights for sub-ego states
        weights = {
            "Parent-in-Parent": 3, "Adult-in-Parent": 3, "Child-in-Parent": 3,
            "Parent-in-Adult": 2, "Adult-in-Adult": 2, "Child-in-Adult": 2,
            "Parent-in-Child": 1, "Adult-in-Child": 1, "Child-in-Child": 1
        }
        total_weight = sum(weights.values())
    
        # Try to extract the stances (should be a dict: sub_state -> stance)
        stances = {}
        # Try negotiation_results["final_stances"], fallback to ["stance"] in sub-states list
        if negotiation_results and "final_stances" in negotiation_results:
            stances = negotiation_results["final_stances"]
        elif negotiation_results:
            # Fallback: try to infer from negotiation_results (e.g., a list of sub-state dicts)
            for sub in weights:
                stance = negotiation_results.get(sub)
                if isinstance(stance, dict) and "stance" in stance:
                    stances[sub] = stance["stance"]
                elif isinstance(stance, (int, float)):
                    stances[sub] = stance
                # else: skip if not found
    
        # Fill in missing sub-ego stances with 0
        weighted_sum = 0
        for sub, weight in weights.items():
            stance = float(stances.get(sub, 0))  # Default to 0 if missing
            weighted_sum += stance * weight
    
        # Max/min possible sums
        max_possible = 10 * total_weight
        min_possible = -10 * total_weight
    
        # Normalized confidence: -1 (all -10) to +1 (all +10)
        if max_possible - min_possible != 0:
            confidence = (weighted_sum - min_possible) / (max_possible - min_possible) * 2 - 1
        else:
            confidence = 0
    
        recommendation = "Accept" if weighted_sum > 0 else "Reject"
    
        return DecisionResult(
            model_used="Model 2: Second-Order Ego State Negotiations",
            recommendation=recommendation,
            confidence_score=confidence,  # -1..+1 (or you can use abs(confidence) if you want only magnitude)
            conditions=negotiation_results.get(
                "agreed_actions", []) if negotiation_results else [],
            reasoning=f"Weighted sum of stances: {weighted_sum:.2f} (scale: {min_possible} to {max_possible}); Confidence: {confidence:.2f}",
            detailed_analysis={
                "negotiation_results": negotiation_results,
                "weighted_sum": weighted_sum,
                "max_possible": max_possible,
                "min_possible": min_possible,
                "confidence": confidence,
                "stances": stances,
                "weights": weights
            }
        )
    
    
    def _check_tiers_model3(self, problem: str, matrix_data: List[MatrixCell]) -> Tuple[Dict[str, Any], List[str]]:
        '''Check tiers bottom-up for Model 3'''
        levels = {}
        for cell in matrix_data:
            if cell.maslow_level not in levels:
                levels[cell.maslow_level] = []
            levels[cell.maslow_level].append(cell)
        tier_order = ["Physiological", "Safety",
            "Love/Belonging", "Esteem", "Self-Actualization"]
        tier_results = {}
        mitigations = []
        for tier in tier_order:
            if tier in levels:
                scores = [cell.score for cell in levels[tier]]
                min_score = min(scores)
                avg_score = np.mean(scores)
                tier_results[tier] = {
                    "scores": scores,
                    "min_score": min_score,
                    "avg_score": avg_score,
                    "passes": min_score >= 3.0
                }
                if min_score < 3.0:
                    mitigations.append(
                        f"Mitigation needed for {tier} (min score: {min_score})")
        return tier_results, mitigations
    
    def _calculate_utility_model3(self, problem: str, matrix_data: List[MatrixCell], tier_results: Dict[str, Any]) -> DecisionResult:
        '''Calculate final utility score for Model 3 (with scores in -10 to +10 range).'''
        tier_weights = {
            "Physiological": 1,
            "Safety": 2,
            "Love/Belonging": 3,
            "Esteem": 4,
            "Self-Actualization": 5
        }
        total_utility = 0
        max_possible = 0
        min_possible = 0
        for tier, weight in tier_weights.items():
            if tier in tier_results:
                avg_score = tier_results[tier]["avg_score"]
                total_utility += weight * avg_score
                max_possible += weight * 10
                min_possible += weight * -10
    
        # Normalized utility: 0 (all -10s), 0.5 (neutral/zero), 1 (all +10s)
        if max_possible - min_possible > 0:
            scaled_score = (total_utility - min_possible) / (max_possible - min_possible)
        else:
            scaled_score = 0.5  # Default to neutral if denominator is zero (shouldn't happen)
    
        # Accept if net utility is above neutral (scaled_score > 0.5)
        recommendation = "Accept" if scaled_score > 0.5 else "Reject"
    
        # Address any tiers with an average < 0 as "concern"
        conditions = []
        for tier, results in tier_results.items():
            if results["min_score"] < 0:
                conditions.append(
                    f"Address {tier} concerns (min score: {results['min_score']:.1f})"
                )
    
        return DecisionResult(
            model_used="Model 3: Maslow-TA Decision Matrix",
            recommendation=recommendation,
            confidence_score=scaled_score,  # 0 = all -10s, 0.5 = net neutral, 1 = all +10s
            conditions=conditions,
            reasoning=f"Weighted utility: {total_utility:.1f} (range: {min_possible} to {max_possible}); Scaled: {scaled_score:.2f}",
            detailed_analysis={
                "matrix_data": [asdict(cell) for cell in matrix_data],
                "tier_results": tier_results,
                "total_utility": total_utility,
                "max_possible": max_possible,
                "min_possible": min_possible,
                "scaled_score": scaled_score
            }
        )
    

    def _everyday_language_summary_prompt(self, problem: str, model_output: Dict[str, Any]) -> str:
        return f'''
You are an expert at translating technical or psychological reports into clear, plain, everyday language for normal people.
Below is a decision problem and the output of a decision-making model that uses psychology terms. Your job is to summarise, in simple language, what this output means, what the main recommendation is, and why – *without* using Transactional Analysis or psychological jargon.

Original Question:
{problem}

Model Output:
{json.dumps(model_output, indent=2)}

Please summarise in clear, everyday language for a general audience.
    '''
    

    def _is_error(self, data: dict):
        '''Check if a JSON object is an error response from the API.'''
        return "__error__" in data

    def _strip_json_code_block(self, text: str) -> str:
        """
        Extract just the JSON payload from an LLM reply that may contain
        Markdown fences or stray commentary.

        Strategy
        --------
        1. Look for a fenced block  ```json … ```  (or plain ``` … ```).
           If found, return the braces’ contents.
        2. Fallback: locate the first '{' and the last '}' in the reply.
           If that slice parses successfully with json.loads(), return it.
        3. If neither tactic succeeds, give the raw text back so the caller
           can surface a clear “JSON parse error” message.

        The function never raises; it only returns a string.
        """
        import re, json   # local import keeps the method standalone

        text = text.strip()

        # --- 1) fenced ```json``` or ``` block anywhere in the text ----------
        fence = re.search(r"```(?:json)?\s*({.*?})\s*```", text,
                          flags=re.S | re.I)
        if fence:
            return fence.group(1).strip()

        # --- 2) bare JSON object somewhere in the message --------------------
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        first_bracket = text.find('[')
        last_bracket = text.rfind(']')
        # Prefer object if both present, else try array
        if 0 <= first_brace < last_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                json.loads(candidate)
                return candidate.strip()
            except Exception:
                pass
        if 0 <= first_bracket < last_bracket:
            candidate = text[first_bracket:last_bracket + 1]
            try:
                json.loads(candidate)
                return candidate.strip()
            except Exception:
                pass

        # --- 3) give up – let _handle_json_parse() raise a JSON error ---------
        return text

    def _handle_json_parse(self, response):
        '''
        Robustly parse JSON and halt on model-access errors.
        Always returns a dict. Also logs sanitized text and errors.
        '''
        sanitized = self._strip_json_code_block(response)
        log_api_data("API_SANITIZED", sanitized)
        try:
            data = json.loads(sanitized)
            log_api_data("API_PARSED", data)
            
            print("[DEBUG] Raw model response:", response)
            print("[DEBUG] Sanitized for JSON:", sanitized)

            return data
        except Exception as e:
            # Try to fix unescaped control characters
            import re
            def escape_control_chars(s):
                # This escapes literal line breaks and tabs inside strings
                def repl(m):
                    value = m.group(0)
                    return value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                # Only operate inside double-quoted strings
                return re.sub(r'(?<=")(.*?)(?=")', repl, s, flags=re.DOTALL)
            
            sanitized_fixed = escape_control_chars(sanitized)
            try:
                data = json.loads(sanitized_fixed)
                log_api_data("API_PARSED_FIXED", data)
                print("[WARN] Fixed unescaped control chars in JSON.")
                return data
            except Exception as e2:
                print("\nJSON parse error:", e2)
                print("Raw response was:\n", sanitized, "\n")
                log_api_data("API_JSON_ERROR", {
                             "exception": str(e2), "raw": sanitized})
                if "model" in sanitized and ("not available" in sanitized or "not found" in sanitized):
                    print(
                        "\n*** ERROR: The OpenAI API key you are using does not have access to the model you requested. ***")
                    print(
                        "-> Try a different model (such as gpt-3.5-turbo, gpt-4o, or check your account entitlements).")
                    print(
                        "-> See https://platform.openai.com/docs/models for current options, or upgrade your plan if needed.")
                    sys.exit(1)
                if "You do not have access" in sanitized:
                    print(
                        "\n*** ERROR: Your API key does not have access to this model. ***")
                    print("-> Try a different model or upgrade your account.")
                    sys.exit(1)
                return {"__error__": f"JSON parse error: {str(e2)}"}

    def _call_openai_api(self, prompt: str) -> str:
        '''Make API call to OpenAI v1.x API and handle model access errors. Also log every return.'''
        try:
            response = openai.chat.completions.create(
                # === MODEL OPTIONS (uncomment ONE) ===

                # GPT-4.1 Turbo (high quality, efficient)
                model="gpt-4-1106-preview",

                # model="gpt-4o",
                # model="gpt-3.5-turbo",

                messages=[
                    {"role": "system", "content": "You are an expert in Transactional Analysis and decision-making psychology. Always respond with valid JSON as requested, or with Markdown when asked for a summary."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            content = response.choices[0].message.content.strip(
            ) if response.choices else ""
            # DEBUG: See what the model sends
            print(f"API raw response: {content!r}")
            log_api_data("API_RAW", content)
            return content
        except Exception as e:
            error_str = str(e)
            print(f"OpenAI API Error: {error_str}")
            log_api_data("API_ERROR", error_str)
            # Handle "model not available" or "not found" error explicitly
            if ("model" in error_str and "not available" in error_str) or \
               ("model" in error_str and "not found" in error_str) or \
               ("You do not have access" in error_str):
                print(
                    "\n*** ERROR: The OpenAI API key you are using does not have access to the model you requested. ***")
                print(
                    "-> Try a different model (such as gpt-3.5-turbo, gpt-4o, or check your account entitlements).")
                print(
                    "-> See https://platform.openai.com/docs/models for current options, or upgrade your plan if needed.")
                sys.exit(1)
            return json.dumps({"__error__": error_str})

    def _execute_model1(self, problem: str, options, doc, considerations, log_callback=None) -> DecisionResult:
        if log_callback: log_callback("start", {"model": "model1", "problem": problem})
        print("Executing Model 1: Democratic Ego State Council")
        ego_responses = []
        for ego_state in self.workflows[DecisionModel.DEMOCRATIC_COUNCIL]["ego_states"]:
            response = self._call_openai_api(self._ego_state_prompt(problem, ego_state, options))
            if log_callback: log_callback("ego_response", {"ego_state": ego_state, "raw_response": response})
            if doc:
                doc.add_heading(f"{ego_state} Ego State Analysis", level=3)
                try:
                    parsed = json.loads(self._strip_json_code_block(response))
                    for k, v in parsed.items():
                        doc.add_paragraph(f"{k}: {v}")
                except Exception:
                    doc.add_paragraph(f"Raw: {response}")
            data = self._handle_json_parse(response)
            if self._is_error(data):
                print("API call failed for ego state:", ego_state, data["__error__"])
                ego_responses.append(
                    EgoStateResponse(
                        ego_state=ego_state,
                        concerns=[],
                        hopes=[],
                        fears=[],
                        score=0.0,
                        reasoning="API call failed: " + data["__error__"]
                    )
                )
            else:
                ego_responses.append(
                    map_fields_by_id({**{"ego_state": ego_state}, **data}, EGO_FIELDS_BY_ID, EgoStateResponse)
                )
            # Log considerations as steps if logging enabled
            resp = ego_responses[-1]
            field_map = [
                ("concerns", "1"),
                ("hopes",    "2"),
                ("fears",    "3"),
                # Add others as needed (e.g., "reasoning"/"5" if you want, but you'll filter these out)
            ]
    
            for attr, field_id in field_map:
                items = getattr(resp, attr, [])
                orientation = FIELD_ID_TO_ORIENTATION[field_id]
                for item in items:
                    if isinstance(item, dict):
                        c = Consideration(
                            text=item.get("text", str(item)),
                            source_model="model1",
                            source_context=resp.ego_state,
                            orientation=orientation,
                            score=signed_score(orientation, resp.score),
                            option=item.get("option"),
                            field_id=field_id
                        )
                    else:
                        c = Consideration(
                            text=item,
                            source_model="model1",
                            source_context=resp.ego_state,
                            orientation=orientation,
                            score=signed_score(orientation, resp.score),
                            option=None,
                            field_id=field_id
                        )
                    considerations.append(c)
                    if log_callback: log_callback("consideration", asdict(c))
    
        synthesis_resp = self._call_openai_api(self._council_synthesis_prompt(problem, ego_responses))
        if log_callback: log_callback("council_synthesis", {"raw_response": synthesis_resp})
        if doc:
            doc.add_heading("Council Synthesis", level=3)
            try:
                parsed = json.loads(self._strip_json_code_block(synthesis_resp))
                for k, v in parsed.items():
                    doc.add_paragraph(f"{k}: {v}")
            except Exception:
                doc.add_paragraph(f"Raw: {synthesis_resp}")
        synthesis = self._handle_json_parse(synthesis_resp)
        if self._is_error(synthesis):
            print("API call failed for council synthesis:", synthesis["__error__"])
            synthesis = {
                "shared_themes": [],
                "tension_points": [],
                "mitigation_plans": [],
                "consensus_level": 0,
                "synthesis_reasoning": "API call failed: " + synthesis["__error__"]
            }
        if log_callback: log_callback("synthesis_parsed", synthesis)
        decision = self._make_final_decision_model1(problem, ego_responses, synthesis)
        if log_callback: log_callback("final_decision", asdict(decision))
    
        print(f"[DEBUG] considerations: {[asdict(c) for c in considerations]}")
    
        return decision
    

    def _execute_model2(self, problem: str, options, doc, considerations, log_callback=None) -> DecisionResult:
        if log_callback: log_callback("start", {"model": "model2", "problem": problem})
        print("Executing Model 2: Second-Order Ego State Negotiations")
        sub_ego_responses = []
        for sub_state in self.workflows[DecisionModel.SECOND_ORDER_NEGOTIATIONS]["sub_ego_states"]:
            response = self._call_openai_api(self._sub_ego_state_prompt(problem, sub_state, options))
            if log_callback: log_callback("sub_ego_response", {"sub_state": sub_state, "raw_response": response})
            if doc:
                doc.add_heading(f"{sub_state} Sub-Ego Analysis", level=3)
                try:
                    parsed = json.loads(self._strip_json_code_block(response))
                    for k, v in parsed.items():
                        doc.add_paragraph(f"{k}: {v}")
                except Exception:
                    doc.add_paragraph(f"Raw: {response}")
            data = self._handle_json_parse(response)
            if self._is_error(data):
                print("API call failed for sub-ego state:", sub_state, data["__error__"])
                sub_ego_responses.append(
                    SubEgoStateResponse(
                        sub_state=sub_state,
                        core_function="API call failed",
                        concerns=[],
                        stance=0,
                        non_negotiables=[],
                        reasoning="API call failed: " + data["__error__"]
                    )
                )
            else:
                sub_ego_responses.append(
                    map_fields_by_id(
                        {**{"sub_state": sub_state, "core_function": self._sub_ego_state_desc(sub_state)}, **data},
                        SUBEGO_FIELDS_BY_ID, SubEgoStateResponse)
                )
            resp = sub_ego_responses[-1]
            # Unified consideration creation
            field_map = [
                ("concerns", "1"),
                ("non_negotiables", "3"),
                # "stance" ("2") is numeric, skip as not a textual consideration
                # "reasoning" ("4") can be omitted from consideration objects (unless you want to record, but you'll filter them later)
            ]
            for attr, field_id in field_map:
                items = getattr(resp, attr, [])
                orientation = FIELD_ID_TO_ORIENTATION[field_id]
                # "concerns" orientation is "positive" if stance>0 else "negative"
                for item in items:
                    # The stance field (int) is used as the "score" for all these
                    # But we want to flip negatives
                    final_orientation = orientation if field_id != "1" else ("positive" if resp.stance > 0 else "negative")
                    if isinstance(item, dict):
                        c = Consideration(
                            text=item.get("text", str(item)),
                            source_model="model2",
                            source_context=resp.sub_state,
                            orientation=final_orientation,
                            score=signed_score(final_orientation, resp.stance),
                            option=item.get("option"),
                            field_id=field_id
                        )
                    else:
                        c = Consideration(
                            text=item,
                            source_model="model2",
                            source_context=resp.sub_state,
                            orientation=final_orientation,
                            score=signed_score(final_orientation, resp.stance),
                            option=None,
                            field_id=field_id
                        )
                    considerations.append(c)
                    if log_callback: log_callback("consideration", asdict(c))
            # If you want to store "reasoning" as well (field_id="4"), do a similar loop,
            # but you will filter these out before reporting.
    
        cluster_results_resp = self._call_openai_api(self._cluster_dialogues_prompt(problem, sub_ego_responses))
        if log_callback: log_callback("cluster_dialogues", {"raw_response": cluster_results_resp})
        if doc:
            doc.add_heading("Cluster Dialogues", level=3)
            try:
                parsed = json.loads(self._strip_json_code_block(cluster_results_resp))
                for k, v in parsed.items():
                    doc.add_paragraph(f"{k}: {v}")
            except Exception:
                doc.add_paragraph(f"Raw: {cluster_results_resp}")
        cluster_results = self._handle_json_parse(cluster_results_resp)
        if self._is_error(cluster_results):
            print("API call failed for cluster dialogues:", cluster_results["__error__"])
            cluster_results = {}
        if log_callback: log_callback("cluster_dialogues_parsed", cluster_results)
        negotiation_results_resp = self._call_openai_api(self._cross_cluster_negotiation_prompt(problem, cluster_results))
        if log_callback: log_callback("cross_cluster_negotiation", {"raw_response": negotiation_results_resp})
        if doc:
            doc.add_heading("Cross-Cluster Negotiation", level=3)
            try:
                parsed = json.loads(self._strip_json_code_block(negotiation_results_resp))
                for k, v in parsed.items():
                    doc.add_paragraph(f"{k}: {v}")
            except Exception:
                doc.add_paragraph(f"Raw: {negotiation_results_resp}")
        negotiation_results = self._handle_json_parse(negotiation_results_resp)
        if self._is_error(negotiation_results):
            print("API call failed for cross-cluster negotiation:", negotiation_results["__error__"])
            negotiation_results = {}
        if log_callback: log_callback("negotiation_results_parsed", negotiation_results)
        final_decision = self._conduct_weighted_vote_model2(problem, negotiation_results)
        if log_callback: log_callback("final_decision", asdict(final_decision))
    
        print(f"[DEBUG] considerations: {[asdict(c) for c in considerations]}")
    
        return final_decision
    

    def _execute_model3(self, problem: str, options, doc, considerations, log_callback=None) -> DecisionResult:
        if log_callback: log_callback("start", {"model": "model3", "problem": problem})
        print("Executing Model 3: Maslow-TA Decision Matrix")
        matrix_cells = []
        for ego_state in ["Parent", "Adult", "Child"]:
            for maslow_level, desc in [
                ("Physiological", "Basic survival needs: money, food, shelter, rest"),
                ("Safety", "Security, stability, health, protection from risk"),
                ("Love/Belonging", "Family, friends, community, social connection"),
                ("Esteem", "Status, recognition, mastery, achievement, respect"),
                ("Self-Actualization", "Purpose, growth, creativity, fulfilling potential")
            ]:
                prompt = self._matrix_cell_prompt(problem, ego_state, maslow_level, desc, options)
                response = self._call_openai_api(prompt)
    
                if log_callback: log_callback("matrix_cell", {"ego_state": ego_state, "maslow_level": maslow_level, "raw_response": response})
                if doc:
                    doc.add_heading(f"{ego_state} x {maslow_level} Cell Analysis", level=3)
                    try:
                        parsed = json.loads(self._strip_json_code_block(response))
                        for k, v in parsed.items():
                            doc.add_paragraph(f"{k}: {v}")
                    except Exception:
                        doc.add_paragraph(f"Raw: {response}")
    
                parsed_preview = self._handle_json_parse(response)
                if not self._is_error(parsed_preview):
                    # ----------- ALWAYS handle all items in the cell -----------
                    cell_items = []
                    if isinstance(parsed_preview, dict):
                        cell_items = [parsed_preview]
                    elif isinstance(parsed_preview, list) and all(isinstance(x, dict) for x in parsed_preview):
                        cell_items = parsed_preview
                        print(f"[INFO] LLM returned a list for matrix cell; processing all {len(cell_items)} items.")
                    else:
                        print("[WARN] Unexpected LLM response type; skipping.")
                        cell_items = []
                    for item in cell_items:
                        score = extract_numeric(item.get("1", 0.0))
                        reasoning = item.get("2", "")
                        option = None
                        if isinstance(reasoning, dict):
                            text = reasoning.get("text", "")
                            option = reasoning.get("option", None)
                        else:
                            text = reasoning
                        orientation = "positive" if score > 0 else ("negative" if score < 0 else "neutral")
                        # Use signed_score so negatives are actually negative
                        true_score = signed_score(orientation, score)
                        c = Consideration(
                            text=text,
                            source_model="model3",
                            source_context=f"{ego_state}-{maslow_level}",
                            orientation=orientation,
                            score=true_score,
                            option=option
                        )
                        considerations.append(c)
                        if log_callback:
                            log_callback("consideration", asdict(c))
    
                # ----------- Also store all MatrixCell(s) -----------
                data = self._handle_json_parse(response)
                if self._is_error(data):
                    print(f"API call failed for {ego_state} x {maslow_level}:", data["__error__"])
                    matrix_cells.append(
                        MatrixCell(
                            ego_state=ego_state,
                            maslow_level=maslow_level,
                            score=0.0,
                            reasoning="API call failed: " + data["__error__"]
                        )
                    )
                else:
                    # Always treat as list of dicts or single dict
                    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
                        for item in data:
                            score = extract_numeric(item.get("1", 0.0))
                            reasoning = item.get("2", "")
                            if isinstance(reasoning, dict):
                                text = reasoning.get("text", "")
                            else:
                                text = reasoning
                            matrix_cells.append(
                                MatrixCell(
                                    ego_state=ego_state,
                                    maslow_level=maslow_level,
                                    score=signed_score("positive" if score > 0 else ("negative" if score < 0 else "neutral"), score),
                                    reasoning=text
                                )
                            )
                    elif isinstance(data, dict):
                        score = extract_numeric(data.get("1", 0.0))
                        reasoning = data.get("2", "")
                        if isinstance(reasoning, dict):
                            text = reasoning.get("text", "")
                        else:
                            text = reasoning
                        matrix_cells.append(
                            MatrixCell(
                                ego_state=ego_state,
                                maslow_level=maslow_level,
                                score=signed_score("positive" if score > 0 else ("negative" if score < 0 else "neutral"), score),
                                reasoning=text
                            )
                        )
                    else:
                        print(f"[WARN] Unexpected matrix cell data structure for {ego_state} x {maslow_level}: {type(data)}")
                        matrix_cells.append(
                            MatrixCell(
                                ego_state=ego_state,
                                maslow_level=maslow_level,
                                score=0.0,
                                reasoning="Unexpected matrix cell data structure."
                            )
                        )
        if log_callback: log_callback("matrix_cells_collected", [asdict(cell) for cell in matrix_cells])
        tier_results, mitigations = self._check_tiers_model3(problem, matrix_cells)
        if log_callback: log_callback("tier_results", {"tier_results": tier_results, "mitigations": mitigations})
        if mitigations:
            for m in mitigations:
                print("Mitigation needed:", m)
                if doc:
                    doc.add_paragraph(f"Mitigation needed: {m}", style="Intense Quote")
        final_decision = self._calculate_utility_model3(problem, matrix_cells, tier_results)
        if log_callback: log_callback("final_decision", asdict(final_decision))
        
        print(f"[DEBUG] considerations: {[asdict(c) for c in considerations]}")
    
        return final_decision
    
    
    
    def execute_workflow(self, model: DecisionModel, problem: str, options, doc, considerations=None, log_callback=None) -> DecisionResult:
        if model == DecisionModel.DEMOCRATIC_COUNCIL:
            return self._execute_model1(problem, options, doc, considerations, log_callback)
        elif model == DecisionModel.SECOND_ORDER_NEGOTIATIONS:
            return self._execute_model2(problem, options, doc, considerations, log_callback)
        elif model == DecisionModel.MASLOW_TA_MATRIX:
            return self._execute_model3(problem, options, doc, considerations, log_callback)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    


    # ==== Prompt construction helpers with numeric IDs ====

    def _ego_state_prompt(self, problem, ego_state, options):
        option_str = "\n".join([f"- {opt['text']}" for opt in options])
        return f'''
You are analyzing a decision problem from the perspective of the {ego_state} ego state in Transactional Analysis.

Problem: {problem}
Options:
{option_str}

For each concern, hope, or fear, specify *exactly which option it applies to* by copying the full text of the option from the list above (do not make up new text or use abbreviations).

Respond with valid JSON and these keys ONLY (use the numeric IDs):
1: [{{"text": "...", "option": "Paste the *exact* option text here"}}, ...]  (main concerns from this perspective)
2: [{{"text": "...", "option": "Paste the *exact* option text here"}}, ...]  (positive outcomes hoped for)
3: [{{"text": "...", "option": "Paste the *exact* option text here"}}, ...]  (negative outcomes feared)
4: numerical score from -10 (strongly against) to +10 (strongly for)
5: detailed explanation of this ego state's analysis and position

Example:
{{
  "1": [{{"text": "concern a", "option": "Option Text Here 1"}}, {{"text": "concern b", "option": "Option Text Here 2"}}],
  "2": [{{"text": "hope a", "option": "Option Text Here 3"}}],
  "3": [{{"text": "fear a", "option": "Option Text Here 1"}}],
  "4": 3,
  "5": "long explanation here"
}}
'''

    def _council_synthesis_prompt(self, problem, ego_responses):
        return f'''
Synthesize the perspectives from all three ego states into a coherent council discussion.

Problem: {problem}

Ego State Responses:
{json.dumps([asdict(response) for response in ego_responses], indent=2)}

Identify shared themes, points of agreement, tension points, and propose mitigation plans.

Provide your synthesis in JSON format:
{{
    "shared_themes": ["list of themes all ego states agree on"],
    "tension_points": ["list of areas where ego states disagree"],
    "mitigation_plans": ["list of specific actions to address tensions"],
    "consensus_level": "score from 1-5 indicating how much agreement exists",
    "synthesis_reasoning": "detailed explanation of the council synthesis"
}}
'''

    def _sub_ego_state_desc(self, sub_state):
        sub_state_descriptions = {
            "Parent-in-Parent": "Moral authority and tradition, core values",
            "Adult-in-Parent": "Experienced rationality filtered through values",
            "Child-in-Parent": "Rules of conformity, following proper procedures",
            "Parent-in-Adult": "Structured problem-solving with ethical considerations",
            "Adult-in-Adult": "Pure data-driven analysis and logical reasoning",
            "Child-in-Adult": "Inventive curiosity within rational thinking",
            "Parent-in-Child": "Internalized rules about play and appropriate behavior",
            "Adult-in-Child": "Logical yet playful analysis, learning excitement",
            "Child-in-Child": "Pure spontaneity, emotion, and authentic desires"
        }
        return sub_state_descriptions.get(sub_state, "Unknown")

    def _sub_ego_state_prompt(self, problem, sub_state, options):
        option_str = "\n".join([f"- {opt['text']}" for opt in options]) if options else ""
        return f'''
You are analyzing a decision problem from the perspective of the {sub_state} sub-ego state in Second-Order Transactional Analysis.

Problem: {problem}
Options:
{option_str}

{sub_state}: {self._sub_ego_state_desc(sub_state)}

For each concern or requirement, specify *exactly which option it applies to* by copying the full text of the option from the list above (do not make up new text or use abbreviations).

Respond with valid JSON and these keys ONLY:
1: [{{"text": "...", "option": "Paste the *exact* option text here"}}, ...]   // (list of main concerns from this sub-state)
2: integer stance from -10 (strongly against) to +10 (strongly for)
3: [{{"text": "...", "option": "Paste the *exact* option text here"}}, ...]   // (list of absolute requirements or red lines)
4: detailed explanation of this sub-state's position

Example:
{{
  "1": [{{"text": "concern a", "option": "Option Text Here 1"}}, {{"text": "concern b", "option": "Option Text Here 2"}}],
  "2": 0,
  "3": [{{"text": "requirement a", "option": "Option Text Here 3"}}],
  "4": "explanation"
}}
'''





    def _cluster_dialogues_prompt(self, problem, sub_ego_responses):
        return f'''
Conduct internal dialogues within clusters to reach agreement.

Problem: {problem}

Cluster Members:
{json.dumps([asdict(member) for member in sub_ego_responses], indent=2)}

Find common ground and negotiate stance changes within clusters.

Provide results in JSON format (group by clusters as needed):
{{
    "cluster_name": "name",
    "main_negotiation_points": ["key issues discussed"],
    "agreed_actions": ["specific agreements reached"],
    "stance_changes": [
        {{"sub_state": "name", "old_stance": 0,
            "new_stance": 1, "reason": "explanation"}}
    ],
    "cluster_consensus": "score from 1-5"
}}
'''

    def _cross_cluster_negotiation_prompt(self, problem, cluster_results):
        return f'''
Conduct cross-cluster negotiations to resolve remaining disagreements.

Problem: {problem}

Cluster Results:
{json.dumps(cluster_results, indent=2)}

Identify remaining concerns and create horse-trading proposals.

Provide results in JSON format:
{{
    "pending_concerns": ["issues still needing resolution"],
    "trade_proposals": [
        {{"concern": "issue", "blocking_voice": "sub-state",
            "proposal": "solution", "result": "outcome"}}
    ],
    "final_stance_changes": [
        {{"sub_state": "name", "old_stance": 0, "new_stance": 1}}
    ],
    "negotiation_success": "score from 1-5"
}}
'''

    def _matrix_cell_prompt(self, problem, ego_state, maslow_level, maslow_desc, options):
        option_str = "\n".join([f"- {opt['text']}" for opt in options]) if options else ""
        return f'''
Evaluate how the decision impacts {maslow_level} needs from the {ego_state} ego state perspective.

Problem: {problem}
Options:
{option_str}

{ego_state} Perspective:
- Parent: Values, morals, social expectations, duty
- Adult: Facts, logic, practical consequences
- Child: Emotions, desires, authenticity, spontaneity

{maslow_level}: {maslow_desc}

Respond in JSON using these keys only:
1: numerical score from -10 (strongly against/negative impact) to +10 (strongly for/positive impact)
2: {{"text": "detailed explanation", "option": "Paste the *exact* option text here"}}  # Explain which option this cell refers to

Example:
{{
  "1": 4,
  "2": {{"text": "explanation here", "option": "Option Text Here 1"}}
}}
'''


    def _summarize_model_output_prompt(self, problem: str, model_output: Dict[str, Any]) -> str:
        '''
        Generates a prompt for the AI to summarize the model's output in Markdown.
        '''
        return f'''
The following is the full output from one of the Transactional Analysis decision models.
Your task is to provide a concise and insightful summary of the model's findings,
recommendation, and reasoning in Markdown format.

Original Decision Problem: {problem}

Model Output:
```json
{json.dumps(model_output, indent=2)}
Please summarize this information, highlighting the key recommendation, confidence,
and any important conditions or detailed analysis. Format your response using Markdown.
'''

####################################################################################################
# Consideration Storage & Indexing
####################################################################################################
from collections import defaultdict
from typing import List, Dict, Optional
import difflib

class ConsiderationProcessor:
    '''
    In-memory indexed storage for all considerations produced by model runs.
    Supports grouping, de-duplication, lookup by option/model/context, and full traceability.
    Used to prepare output tables and cross-reference model results.
    '''
    def __init__(self, logger=print):
        self._table = []  # All considerations as list of dataclass or dict
        self._by_option_text = {}  # str: list[Consideration]
        self._by_option_id = {}    # str: list[Consideration]
        self._by_model = {}        # model: list[Consideration]
        self._by_context = {}      # context: list[Consideration]
        self._general = []         # Not tied to any option
        self.logger = logger

        # Canonical option lists/mapping (populated via set_options)
        self._option_texts = []      # List of canonical option texts
        self._option_id_by_text = {} # Dict: canonical text → ID

    def set_options(self, options: list):
        self._option_texts = [opt['text'] for opt in options]
        self._option_id_by_text = {opt['text']: opt['id'] for opt in options}
        self.logger(f"[ConsiderationDB][set_options] Canonical options: {self._option_texts}")

    def resolve_option(self, raw_option_text):
        if not raw_option_text:
            return None
        if raw_option_text in self._option_texts:
            return raw_option_text
        matches = difflib.get_close_matches(raw_option_text, self._option_texts, n=1, cutoff=0.8)
        if matches:
            self.logger(f"[ConsiderationDB][resolve_option] Fuzzy-matched '{raw_option_text}' to '{matches[0]}'")
            return matches[0]
        self.logger(f"[ConsiderationDB][resolve_option] No match for '{raw_option_text}'")
        return None

    def add(self, cons):
        print("[DEBUG][add] Adding consideration:", cons)
        self._table.append(cons)
        print(f"[DEBUG][add] _table now has {len(self._table)} items.")
        option_text = getattr(cons, 'option', None)
        option_id = getattr(cons, 'option_id', None)
        canonical_option = None
        print(f"[DEBUG][add] option_text: {option_text}, option_id: {option_id}")
        if option_text:
            canonical_option = self.resolve_option(option_text)
            print(f"[DEBUG][add] canonical_option resolved: {canonical_option}")
            if canonical_option:
                cons.option = canonical_option
                self._by_option_text.setdefault(canonical_option, []).append(cons)
                print(f"[DEBUG][add] Added to _by_option_text under {canonical_option}.")
            else:
                self._general.append(cons)
                print(f"[DEBUG][add] Option text not resolved, added to _general.")
        else:
            self._general.append(cons)
            print(f"[DEBUG][add] No option_text, added to _general.")
        if option_id:
            self._by_option_id.setdefault(option_id, []).append(cons)
            print(f"[DEBUG][add] Added to _by_option_id under {option_id}.")
        model = getattr(cons, 'source_model', None)
        if model:
            self._by_model.setdefault(model, []).append(cons)
            print(f"[DEBUG][add] Added to _by_model under {model}.")
        context = getattr(cons, 'source_context', None)
        if context:
            self._by_context.setdefault(context, []).append(cons)
            print(f"[DEBUG][add] Added to _by_context under {context}.")
        self.logger(
            f"[ConsiderationDB][add] Added: model={model}, option_text={option_text}, "
            f"canonical_option={canonical_option}, option_id={option_id}, "
            f"context={context}, orientation={getattr(cons,'orientation',None)}, "
            f"text={getattr(cons,'text','')[:90]}"
        )
        print(f"[DEBUG][add] Completed processing for: {getattr(cons, 'text', '')[:40]}...")

    def add_many(self, conslist):
        print(f"[ConsiderationDB][add_many] Called with {len(conslist)} considerations")
        if not conslist:
            print("[ConsiderationDB][add_many] Warning: Empty list provided.")
        for i, c in enumerate(conslist):
            print(f"[ConsiderationDB][add_many] Adding consideration {i+1}/{len(conslist)}: {getattr(c, 'text', repr(c))[:80]}")
            self.add(c)
        print(f"[ConsiderationDB][add_many] Finished adding all considerations.")

    def all(self):
        return list(self._table)

    def by_option_text(self, option_text):
        cons = self._by_option_text.get(option_text, [])
        self.logger(f"[ConsiderationDB][by_option_text] Queried '{option_text}' -> {len(cons)} found.")
        return cons

    def by_option_id(self, option_id):
        cons = self._by_option_id.get(option_id, [])
        self.logger(f"[ConsiderationDB][by_option_id] Queried '{option_id}' -> {len(cons)} found.")
        return cons

    def by_model(self, model):
        cons = self._by_model.get(model, [])
        self.logger(f"[ConsiderationDB][by_model] Queried '{model}' -> {len(cons)} found.")
        return cons

    def by_context(self, context):
        cons = self._by_context.get(context, [])
        self.logger(f"[ConsiderationDB][by_context] Queried '{context}' -> {len(cons)} found.")
        return cons

    def general(self):
        self.logger(f"[ConsiderationDB][general] Queried -> {len(self._general)} found.")
        return list(self._general)

    def as_table_data(self, conslist):
        return [
            [getattr(c, 'text', ''), getattr(c, 'orientation', ''), str(getattr(c, 'score', ''))]
            for c in conslist
        ]

    def clear(self):
        self._table.clear()
        self._by_option_text.clear()
        self._by_option_id.clear()
        self._by_model.clear()
        self._by_context.clear()
        self._general.clear()
        self.logger("[ConsiderationDB][clear] All data cleared.")

    def dump_summary(self):
        self.logger(f"[ConsiderationDB][dump_summary] {len(self._table)} total considerations.")
        for key, dic in [
            ('option_text', self._by_option_text),
            ('model', self._by_model),
            ('context', self._by_context)
        ]:
            self.logger(f"  - {key}: {list(dic.keys())}")

    

# ========== MAIN DRIVER ==========
# --- Model synopses ---
model_synopses = {
    "model1": (
    "Model 1: Democratic Ego State Council\n"
    "This model simulates a decision as an internal council between the three core ego states of Transactional Analysis: Parent, Adult, and Child. "
    "Each ego state independently considers the problem, then the responses are synthesized into a council discussion. "
    "The final recommendation is based on consensus or majority among the three voices."
),
    "model2": (
    "Model 2: Second-Order Ego State Negotiations\n"
    "This model considers the nuanced perspectives of nine sub-ego states (Parent-in-Parent, Adult-in-Parent, etc.). "
    "It mimics a more complex negotiation process with internal 'clusters' and cross-cluster horse-trading, before arriving at a weighted consensus."
),
    "model3": (
    "Model 3: Maslow-TA Decision Matrix\n"
    "This model evaluates the decision's impact on each ego state, tiered by the levels of Maslow’s Hierarchy of Needs. "
    "The matrix approach highlights where core needs are at risk, and calculates an overall utility score to drive the recommendation."
)
}

def add_spoken_synopsis_to_doc(doc, results):
    '''
    Adds a narrative explanation of each model’s confidence score and result to the Word doc.
    Intended for more accessible/layperson understanding in the report.
    '''
    # Add the spoken-out explanation of each model's confidence score to the docx report.
    doc.add_page_break()
    doc.add_heading("Final Model Comparison & Synopsis", level=1)
    for model_name, result in results.items():
        doc.add_heading(result.model_used, level=2)
        doc.add_paragraph(f"Recommendation: {result.recommendation}")

        if model_name == 'model1':
            avg = result.confidence_score  # -10 to +10
            doc.add_paragraph(
                f"Raw Confidence Score: {avg:.2f} (on a scale of -10 to +10)"
            )
            # Normalized confidence for comparison (0 to 1)
            norm = (avg + 10) / 20.0
            doc.add_paragraph(
                f"Normalized Confidence: {norm:.2f} (scale 0 to 1)"
            )
            # Conditional explanation
            if avg >= 7.5:
                detail = "This indicates a very strong positive consensus among the three ego states. The decision is almost unanimously supported."
            elif avg >= 5.0:
                detail = "This means a strong consensus in favor. Most ego states are clearly for this decision."
            elif avg >= 2.5:
                detail = "This suggests a moderately positive consensus. The group generally supports the decision, but there may be some reservations."
            elif avg > 0:
                detail = "This is a neutral to slightly positive score. The council isn't opposed, but also isn't strongly convinced."
            elif avg == 0:
                detail = "This is a perfectly balanced score. The council is evenly split."
            elif avg > -2.5:
                detail = "This means a mildly negative consensus. The decision is not recommended, but not strongly rejected."
            elif avg > -5.0:
                detail = "This indicates a moderately negative consensus. Most ego states are hesitant or opposed."
            else:
                detail = "This is a strong rejection. Nearly all ego states are against this decision."
            doc.add_paragraph(
                "The Democratic Council model calculates confidence as the average of all ego state votes, with -10 being strongly against, 0 perfectly neutral, and +10 strongly for. " + detail)

        elif model_name == 'model2':
            conf = result.confidence_score  # -1 to +1
            doc.add_paragraph(f"Weighted Confidence: {conf:.2f} (scale -1 to +1)")
            if conf >= 0.8:
                detail = "There is robust agreement among the sub-ego states—clear consensus."
            elif conf >= 0.5:
                detail = "There is broad support, but some disagreement exists."
            elif conf >= 0.1:
                detail = "The outcome is mixed; support is present, but notable dissent remains."
            elif conf == 0:
                detail = "The group is evenly split; acceptance and rejection are balanced."
            elif conf > -0.1:
                detail = "The group is mixed, but slightly tilted negative; rejection is weakly justified."
            elif conf > -0.5:
                detail = "The group is mostly negative; most sub-ego states oppose the decision."
            else:
                detail = "There is no support; the group is unified in rejection."
            doc.add_paragraph(
                "The Second-Order Negotiations model computes a weighted average of sub-ego states' stances, with -1 meaning unanimous rejection, 0 balanced, and +1 unanimous support. " + detail)

        elif model_name == 'model3':
            conf = result.confidence_score  # 0 to 1, with 0.5 as neutral
            doc.add_paragraph(
                f"Utility Score: {conf:.2f} (scale 0 to 1, with 0.5 as neutral, higher is better)"
            )
            if conf >= 0.85:
                detail = "This decision strongly fulfills all levels of Maslow's needs. It is highly beneficial."
            elif conf >= 0.7:
                detail = "The decision fulfills most needs well; only minor issues exist at certain levels."
            elif conf >= 0.55:
                detail = "The decision is adequate; most needs are met, but there are notable areas for improvement."
            elif conf > 0.5:
                detail = "The decision is slightly positive; most core needs are met, though with reservations."
            elif conf == 0.5:
                detail = "The decision is net neutral; benefits and risks are balanced."
            elif conf > 0.4:
                detail = "The decision is risky or marginal; key needs may be left unmet."
            else:
                detail = "The decision fails to meet essential needs at several levels; it is not recommended."
            doc.add_paragraph(
                "The Maslow-TA Matrix model reflects how well the choice satisfies all layers of psychological and practical needs. 0.5 means perfectly neutral (no overall gain or loss), 1 is maximum fulfillment, 0 is maximum risk/negativity. " + detail)

        doc.add_paragraph(f"Conditions/Notes: {result.conditions}")
        doc.add_paragraph(f"Summary Reasoning: {result.reasoning}")


####################################################################################################
# Main Report Generation Driver
####################################################################################################
def main():
    '''
    Main entry point for the Decisionator tool.
    - Prompts user for decision problem statement.
    - Extracts decision options from problem.
    - Runs all TA models and gathers results.
    - Aggregates, deduplicates, and groups all considerations.
    - Writes formatted Word report with tables, summaries, and appendices.
    - Saves output to timestamped DOCX file.
    '''

    if OPENAI_API_KEY == "your-openai-api-key-here":
        print("ERROR: Please set your OpenAI API key in the OPENAI_API_KEY variable")
        return

    # Prompt user for problem
    print("Please enter the decision problem you want to analyze.")
    print("To finish, press Enter twice on consecutive empty lines (i.e., press Enter, then press Enter again):")
    problem_lines = []
    empty_line_count = 0
    while True:
        line = input()
        if not line:
            empty_line_count += 1
            if empty_line_count >= 2:
                break
        else:
            empty_line_count = 0
            problem_lines.append(line)
    problem = "\n".join(problem_lines).strip()
    while not problem:
        print("The question cannot be blank. Please enter a valid question.")
        print("Please enter the decision problem you want to analyze.")
        print("To finish, press Enter twice on consecutive empty lines (i.e., press Enter, then press Enter again):")
        problem_lines = []
        empty_line_count = 0
        while True:
            line = input()
            if not line:
                empty_line_count += 1
                if empty_line_count >= 2:
                    break
            else:
                empty_line_count = 0
                problem_lines.append(line)
        problem = "\n".join(problem_lines).strip()

    docasm = DocAssembler()
    controller = WorkflowController()
    processor = ConsiderationProcessor()

    # ==== NEW: Decision Problem section (H1), Question (H2), Options (H2) ====
    docasm.add_heading("Problem Statement", level=1)
    docasm.add_heading("Original Question", level=2)
    if is_markdown(problem):
        docasm.add_markdown(problem)
    else:
        docasm.add_paragraph(problem.strip())

    # ==== Extract options for the decision problem ====
    print("\nDetecting decision options in the problem statement...")
    options = controller.extract_options(problem)
    if not options:
        print("No options were extracted from the problem. Please rephrase your problem or check your input.")
        sys.exit(1)
    print("Options detected:")
    for opt in options:
        print(f"{opt['id']}: {opt['text']}")

    # --- Print Options as their own section ---
    docasm.add_heading("Options Considered", level=2)
    for opt in options:
        docasm.add_paragraph(f"{opt['id']}: {opt['text']}")

    # Set canonical options for consideration mapping
    processor.set_options(options)

    print("\nTA Decision-Making Models Demo")
    print("=" * 50)
    print(f"Problem: {problem}\n")

    models = [
        DecisionModel.DEMOCRATIC_COUNCIL,
        DecisionModel.SECOND_ORDER_NEGOTIATIONS,
        DecisionModel.MASLOW_TA_MATRIX
    ]

    results = {}
    everyday_summaries = {}
    steps_by_model = {}

    # ==== MOVED: All Decision Considerations by Option (Chapter 3) ====
    docasm.add_page_break()
    docasm.add_heading("Decision Considerations (by Option)", level=1)
    docasm.add_paragraph(
        "This section lists every single consideration raised by the models, grouped by decision option. "
        "Each table shows the consideration text, whether it is positive or negative, and any associated score."
    )

    # --- Models run and considerations collected here ---
    for i, model in enumerate(models):
        model_label = model.value
        print(f"\n{'='*10} Running Model {i+1}: {model.name.replace('_', ' ').title()} {'='*10}")
        model_steps = []
        def log_step(step_name, data):
            model_steps.append({'step': step_name, 'data': data})
        temp_considerations = []
        result = controller.execute_workflow(
            model,
            problem,
            options,
            doc=None,
            considerations=temp_considerations,
            log_callback=log_step
        )
        print(f"[MAIN] About to call add_many with {len(temp_considerations)} considerations: {temp_considerations}")
        processor.add_many(temp_considerations)
        results[model_label] = result
        steps_by_model[model_label] = model_steps

        everyday_prompt = controller._everyday_language_summary_prompt(problem, asdict(result))
        everyday_summary = controller._call_openai_api(everyday_prompt)
        everyday_summaries[model_label] = everyday_summary

    # -- Fetch from in-memory processor, grouped by option --
    grouped = {opt['text']: processor.by_option_text(opt['text']) for opt in options}
    general_cons = processor.general()
    all_cons = processor.all()

    ALLOWED_FIELD_IDS = {"1", "2", "3"}

    # ---- Compute normalization for all considerations (across all options) ----
    neg_scores = [float(c.score) for c in all_cons if getattr(c, 'field_id', None) in ALLOWED_FIELD_IDS and c.orientation == "negative" and c.score is not None and float(c.score) < 0]
    pos_scores = [float(c.score) for c in all_cons if getattr(c, 'field_id', None) in ALLOWED_FIELD_IDS and c.orientation == "positive" and c.score is not None and float(c.score) > 0]
    min_neg = min(neg_scores) if neg_scores else -1
    max_pos = max(pos_scores) if pos_scores else 1

    for opt in options:
        opt_text = opt['text']
        conslist = grouped.get(opt_text, [])
        conslist = [c for c in conslist if getattr(c, 'field_id', None) in ALLOWED_FIELD_IDS]
        # Dedupe both exact and near-match
        conslist = dedupe_considerations(conslist)

        docasm.add_heading(f"{opt['id']}: {opt['text']}", level=2)
        if not conslist:
            docasm.add_paragraph("No considerations for this option.")
            continue

        negatives = sorted(
            [c for c in conslist if c.orientation == "negative" and float(c.score) < 0],
            key=lambda x: (float(x.score), str(x.text).lower())
        )
        zeros = sorted(
            [c for c in conslist if float(c.score) == 0],
            key=lambda x: str(x.text).lower()
        )
        positives = sorted(
            [c for c in conslist if c.orientation == "positive" and float(c.score) > 0],
            key=lambda x: (float(x.score), str(x.text).lower())
        )
        ordered_conslist = negatives + zeros + positives

        table = docasm.add_table(rows=1, cols=3)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Consideration'
        hdr_cells[1].text = 'Positive/Negative'
        hdr_cells[2].text = 'Score'

        for row in ordered_conslist:
            row_cells = table.add_row().cells
            row_cells[0].text = str(row.text)
            row_cells[1].text = str(row.orientation)
            row_cells[2].text = str(row.score)
            if float(row.score) < 0 or float(row.score) > 0:
                hexcolor = get_heatmap_color(row.score, min_neg, max_pos, row.orientation)
                if hexcolor:
                    for cell in row_cells:
                        cell._tc.get_or_add_tcPr().append(
                            parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), hexcolor))
                        )
        style_table(table)

    # --- General considerations as usual ---
    docasm.add_heading("General Considerations (Not Tied to a Single Option)", level=2)
    general_cons_short = [c for c in general_cons if getattr(c, 'field_id', None) in ALLOWED_FIELD_IDS]
    general_cons_short = dedupe_considerations(general_cons_short)
    if general_cons_short:
        negatives = sorted(
            [c for c in general_cons_short if c.orientation == "negative" and float(c.score) < 0],
            key=lambda x: (float(x.score), str(x.text).lower())
        )
        zeros = sorted(
            [c for c in general_cons_short if float(c.score) == 0],
            key=lambda x: str(x.text).lower()
        )
        positives = sorted(
            [c for c in general_cons_short if c.orientation == "positive" and float(c.score) > 0],
            key=lambda x: (float(x.score), str(x.text).lower())
        )
        ordered_general = negatives + zeros + positives

        table = docasm.add_table(rows=1, cols=3)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Consideration'
        hdr_cells[1].text = 'Positive/Negative'
        hdr_cells[2].text = 'Score'

        for row in ordered_general:
            row_cells = table.add_row().cells
            row_cells[0].text = str(row.text)
            row_cells[1].text = str(row.orientation)
            row_cells[2].text = str(row.score)
            if float(row.score) < 0 or float(row.score) > 0:
                hexcolor = get_heatmap_color(row.score, min_neg, max_pos, row.orientation)
                if hexcolor:
                    for cell in row_cells:
                        cell._tc.get_or_add_tcPr().append(
                            parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), hexcolor))
                        )
        style_table(table)
    else:
        docasm.add_paragraph("No general considerations were raised.")

    # ==== Chapter 2: Summaries and Conclusions ====
    docasm.add_page_break()
    docasm.add_heading("Summary Conclusions and Recommendations", level=1)
    docasm.add_paragraph(
        "This section collects each model’s everyday-language summary and provides the AI's overall recommendation."
    )

    for model_label in [m.value for m in models]:
        docasm.add_heading(f"{model_label.upper()} Model Summary", level=2)
        docasm.add_markdown(everyday_summaries[model_label])

    overall_prompt = f'''
Here is a decision problem and three different model outputs, each summarized in plain, everyday language.
Your job is to give a clear, everyday-language overall conclusion and recommendation, comparing the different models, and explaining which model's advice makes the most sense in simple, practical terms.

Original Question:
{problem}

Model 1 Summary:
{everyday_summaries.get("model1", "")}

Model 2 Summary:
{everyday_summaries.get("model2", "")}

Model 3 Summary:
{everyday_summaries.get("model3", "")}

**Please give your conclusion and recommendation for a general audience, using clear narrative or bullet points in Markdown. Do not use JSON or code blocks.**
'''
    overall_summary = controller._call_openai_api(overall_prompt)
    docasm.add_heading("Overall Conclusion and Recommendation", level=2)
    docasm.add_markdown(overall_summary)

    # --------- Appendix with Detailed Model Output (NO summary conclusions here) ---------
    docasm.add_page_break()
    docasm.add_heading("Appendix", level=1)
    docasm.add_paragraph(
        "The findings presented in the main part of the document are summarised from the following detailed output from each decision model."
    )

    for i, model in enumerate(models):
        model_label = model.value
        docasm.add_heading(f"Model: {model_label.upper()}", level=2)
        if model_label in model_synopses:
            docasm.add_paragraph(model_synopses[model_label], style='Intense Quote')
        docasm.add_heading("Workthrough", level=3)
        for step in steps_by_model[model_label]:
            docasm.add_heading(f"Step: {step['step']}", level=4)
            if isinstance(step['data'], dict):
                for k, v in step['data'].items():
                    docasm.add_paragraph(f"{k}: {v}")
            else:
                docasm.add_paragraph(str(step['data']))
        docasm.add_heading("Model Result", level=3)
        res = results[model_label]
        docasm.add_paragraph(f"Recommendation: {res.recommendation}")
        docasm.add_paragraph(f"Confidence Score: {res.confidence_score:.2f}")
        docasm.add_paragraph(f"Conditions: {res.conditions}")
        docasm.add_paragraph(f"Reasoning: {res.reasoning}")
        summary_prompt = controller._summarize_model_output_prompt(problem, asdict(res))
        summary_markdown = controller._call_openai_api(summary_prompt)
        docasm.add_heading("AI Summary of Model Results", level=4)
        docasm.add_markdown(summary_markdown)
        if i < len(models) - 1:
            docasm.add_page_break()

    # --------- Save document ---------
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"TA_Decision_Report_[{timestamp}].docx"
    docasm.save(output_filename)
    print(f"\nReport saved as {output_filename}")
    return results

def explain_results_speech(results):
    '''
    Print a spoken-out explanation of each model's confidence score and recommendation,
    and explain what each particular score denotes.
    '''
    for model_name, result in results.items():
        print("=" * 60)
        print(f"Model: {result.model_used}")
        print(f"Recommendation: {result.recommendation}")

        if model_name == 'model1':
            avg = result.confidence_score  # -10 to +10
            norm = (avg + 10) / 20.0      # Normalized to 0..1
            print(f"Raw Confidence Score: {avg:.2f} (on a scale of -10 to +10)")
            print(f"Normalized Confidence: {norm:.2f} (scale 0 to 1)")
            # Detailed conditional explanation:
            if avg >= 7.5:
                detail = "This indicates a *very strong* positive consensus among the three ego states. The decision is almost unanimously supported."
            elif avg >= 5.0:
                detail = "This means a *strong* consensus in favor. Most ego states are clearly for this decision."
            elif avg >= 2.5:
                detail = "This suggests a *moderately positive* consensus. The group generally supports the decision, but there may be some reservations."
            elif avg > 0:
                detail = "This is a *neutral* to slightly positive score. The council isn't opposed, but also isn't strongly convinced."
            elif avg == 0:
                detail = "This is a *perfectly balanced* score. The council is evenly split."
            elif avg > -2.5:
                detail = "This means a *mildly negative* consensus. The decision is not recommended, but not strongly rejected."
            elif avg > -5.0:
                detail = "This indicates a *moderately negative* consensus. Most ego states are hesitant or opposed."
            else:
                detail = "This is a *strong rejection*. Nearly all ego states are against this decision."
            print(
                "The Democratic Council model calculates confidence as the average of all ego state votes, "
                "with -10 being strongly against, 0 perfectly neutral, and +10 strongly for. " + detail
            )

        elif model_name == 'model2':
            conf = result.confidence_score  # -1 to +1
            print(f"Weighted Confidence: {conf:.2f} (scale -1 to +1)")
            if conf >= 0.8:
                detail = "There is *robust agreement* among the sub-ego states—clear consensus."
            elif conf >= 0.5:
                detail = "There is *broad support*, but some disagreement exists."
            elif conf >= 0.1:
                detail = "The outcome is *mixed*; support is present, but notable dissent remains."
            elif conf == 0:
                detail = "The group is *evenly split*; acceptance and rejection are balanced."
            elif conf > -0.1:
                detail = "The group is *mixed*, but slightly tilted negative; rejection is weakly justified."
            elif conf > -0.5:
                detail = "The group is *mostly negative*; most sub-ego states oppose the decision."
            else:
                detail = "There is *no support*; the group is unified in rejection."
            print(
                "The Second-Order Negotiations model computes a weighted average of sub-ego states' stances, "
                "with -1 meaning unanimous rejection, 0 balanced, and +1 unanimous support. " + detail
            )

        elif model_name == 'model3':
            conf = result.confidence_score  # 0 to 1, with 0.5 as neutral
            print(f"Utility Score: {conf:.2f} (scale 0 to 1, with 0.5 as neutral, higher is better)")
            if conf >= 0.85:
                detail = "This decision *strongly* fulfills all levels of Maslow's needs. It is highly beneficial."
            elif conf >= 0.7:
                detail = "The decision fulfills most needs *well*; only minor issues exist at certain levels."
            elif conf >= 0.55:
                detail = "The decision is *adequate*; most needs are met, but there are notable areas for improvement."
            elif conf > 0.5:
                detail = "The decision is *slightly positive*; most core needs are met, though with reservations."
            elif conf == 0.5:
                detail = "The decision is *net neutral*; benefits and risks are balanced."
            elif conf > 0.4:
                detail = "The decision is *risky or marginal*; key needs may be left unmet."
            else:
                detail = "The decision fails to meet *essential needs* at several levels; it is not recommended."
            print(
                "The Maslow-TA Matrix model reflects how well the choice satisfies all layers of psychological and practical needs. "
                "0.5 means perfectly neutral (no overall gain or loss), 1 is maximum fulfillment, 0 is maximum risk/negativity. " + detail
            )
        print(f"Conditions/Notes: {result.conditions}")
        print(f"Summary Reasoning: {result.reasoning}")
        print()


####################################################################################################
# Script Entry Point
####################################################################################################
if __name__ == "__main__":
    main()
