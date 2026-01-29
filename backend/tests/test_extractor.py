import pytest
from unittest.mock import MagicMock, patch
from src.extraction.extractor import SkillExtractor

# Mock Data
MOCK_ALIASES = [
    ("Python", "uuid-1", "Python"),
    ("React", "uuid-2", "React"),
    ("React.js", "uuid-2", "React"),
    ("Go", "uuid-3", "GoLang"), # Canonical Name diff from Alias
]

@patch("src.extraction.extractor.psycopg2.connect")
def test_load_dictionary(mock_connect):
    """
    Verifies that the extractor loads aliases from the DB into FlashText.
    """
    # Setup Mock
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = MOCK_ALIASES
    
    # Initialize
    extractor = SkillExtractor(db_url="mock://url")
    
    # Check if keywords are loaded
    # "Python" should exist
    assert "Python" in extractor.keyword_processor
    # "React.js" should map to "uuid-2|React"
    assert "React.js" in extractor.keyword_processor
    
    # Verify SQL was executed
    mock_cur.execute.assert_called_once()
    
@patch("src.extraction.extractor.psycopg2.connect")
def test_extraction_logic(mock_connect):
    """
    Test the Golden Path: Extracting skills from text.
    """
    # Setup Mock
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = MOCK_ALIASES
    
    extractor = SkillExtractor(db_url="mock://url")
    
    text = "We are looking for a Python developer who knows React.js and maybe Go."
    result = extractor.extract(text)
    
    assert result.processed_text_length == len(text)
    assert len(result.entities) == 3
    
    # Entity 1: Python
    e1 = result.entities[0]
    assert e1.canonical_name == "Python"
    assert e1.skill_id == "uuid-1"
    assert e1.verbatim_text == "Python"
    assert e1.match_method == "exact_dictionary"
    
    # Entity 2: React.js
    e2 = result.entities[1]
    assert e2.canonical_name == "React" # Canonical
    assert e2.skill_id == "uuid-2"
    assert e2.verbatim_text == "React.js" # Alias found
    
    # Entity 3: Go
    e3 = result.entities[2]
    assert e3.canonical_name == "GoLang"
    assert e3.verbatim_text == "Go"
