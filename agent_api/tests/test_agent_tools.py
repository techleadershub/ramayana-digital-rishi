import unittest
from unittest.mock import MagicMock, patch
import sys
import os

import sys
import os

# Add 'agent_api' directory to path explicitly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import search_principles, search_narrative, get_verse_context
from database import SessionLocal, Verse

class TestAgentTools(unittest.TestCase):
    
    @patch('tools.get_searcher')
    def test_search_principles_success(self, mock_get_searcher):
        # Mock Searcher
        mock_searcher = MagicMock()
        mock_get_searcher.return_value = mock_searcher
        
        # Mock Results
        mock_searcher.rag_search.return_value = [
            {
                'verse_id': 1,
                'kanda': 'Bala',
                'sarga': 1,
                'shloka': 1,
                'text': 'Sanskrit Text',
                'explanation': 'Explanation Text',
                'modern_take': 'Be good.',
                'relevance_reason': 'Relevant'
            }
        ]
        
        result = search_principles.invoke("test query")
        
        self.assertIn("Verse: 1", result)
        self.assertIn("Location: Bala 1:1", result)
        self.assertIn("Be good", result)
        
    @patch('tools.SessionLocal')
    def test_search_narrative_success(self, mock_session_cls):
        # Mock DB Session
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        
        # Mock Query Chain: session.query(...) -> mock_query
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        mock_filter = mock_query.filter.return_value
        # If filter is called again (chained), it should return the same filter mock or query mock?
        # In tools.py: q.filter(...).filter(...) -> so filter should return itself or similar
        mock_filter.filter.return_value = mock_filter
        
        mock_limit = mock_filter.limit.return_value
        
        # Mock DB Object
        mock_verse = MagicMock()
        mock_verse.kanda = 'Ayodhya'
        mock_verse.sarga = 10
        mock_verse.verse_number = 5
        mock_verse.speaker = 'Rama'
        # Note: In tools.py it uses r.explanation
        mock_verse.explanation = 'I am going to forest.'
        
        mock_limit.all.return_value = [mock_verse]
        
        result = search_narrative.invoke({"query": "forest", "speaker": "Rama"})
        
        # Debug print
        if "Location: Ayodhya 10:5" not in result:
             print(f"\n\n[DEBUG] Actual Result: {result}\n\n")
        
        self.assertIn("Location: Ayodhya 10:5", result)
        self.assertIn("Speaker: Rama", result)
        self.assertIn("I am going to forest", result)

    @patch('tools.SessionLocal')
    def test_search_narrative_empty(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        
        result = search_narrative.invoke({"query": "nonexistent"})
        self.assertEqual(result, "No narrative verses found.")

if __name__ == '__main__':
    unittest.main()
