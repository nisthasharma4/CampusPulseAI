"""Unit and regression tests for dashboard Subject Syllabus Progress HTML card rendering."""

from unittest.mock import MagicMock, patch
import pytest

from utils.ui import build_subject_card_html, render_subject_card


class TestSubjectCardRendering:
    """Test suite for Subject Syllabus Progress Card HTML generation and rendering."""

    def test_ds_with_two_topics_in_progress(self):
        """Scenario 1: DS with two topics, none completed yet."""
        subject = {"id": 2, "subject_name": "DS", "subject_code": "VS101"}
        progress = {
            "total_topics": 2,
            "completed_topics": 0,
            "in_progress_topics": 1,
            "pending_topics": 2,
            "completion_percentage": 0.0,
        }
        study_hours = 1.0

        html_out = build_subject_card_html(subject, progress, study_hours)

        assert "DS" in html_out
        assert "VS101" in html_out
        assert "0/2 Topics" in html_out
        assert "0%" in html_out
        assert "1.0 hrs" in html_out
        assert "Active" in html_out
        assert "cp-subject-card-v41" in html_out
        assert "empty-topics" not in html_out
        # Verify valid HTML tags
        assert html_out.startswith('<div class="cp-subject-card-v41"')
        assert html_out.endswith("</div></div>")

    def test_dsa_with_two_topics_partially_completed(self):
        """Scenario 2: Dsa with two topics, 1 completed (50%)."""
        subject = {"id": 3, "subject_name": "Dsa", "subject_code": "BD101"}
        progress = {
            "total_topics": 2,
            "completed_topics": 1,
            "in_progress_topics": 1,
            "pending_topics": 1,
            "completion_percentage": 50.0,
        }
        study_hours = 3.5

        html_out = build_subject_card_html(subject, progress, study_hours)

        assert "Dsa" in html_out
        assert "BD101" in html_out
        assert "1/2 Topics" in html_out
        assert "50%" in html_out
        assert "3.5 hrs" in html_out
        assert "In Progress" in html_out
        assert "style=\"width: 50.0%;\"" in html_out

    def test_coa_with_zero_topics_empty_state(self):
        """Scenario 3: COA with zero topics and missing subject code."""
        subject = {"id": 4, "subject_name": "coa", "subject_code": None}
        progress = {
            "total_topics": 0,
            "completed_topics": 0,
            "in_progress_topics": 0,
            "pending_topics": 0,
            "completion_percentage": 0.0,
        }
        study_hours = 0.0

        html_out = build_subject_card_html(subject, progress, study_hours)

        # Requirements:
        # Subject: COA
        # Syllabus Progress: No topics added
        # Progress: 0%
        # Study Time: 0.0 hrs
        # Status: Add Topics
        assert "coa" in html_out
        assert "No Code" in html_out
        assert "No topics added" in html_out
        assert "0%" in html_out
        assert "0.0 hrs" in html_out
        assert "Add Topics" in html_out
        assert "empty-topics" in html_out
        assert "#E9B67D" in html_out  # Distinct apricot border for empty state
        assert "width: 0.0%;" in html_out

    def test_subject_with_all_topics_completed(self):
        """Scenario 4: Subject with all topics completed (100%)."""
        subject = {"id": 5, "subject_name": "Operating Systems", "subject_code": "CS302"}
        progress = {
            "total_topics": 4,
            "completed_topics": 4,
            "in_progress_topics": 0,
            "pending_topics": 0,
            "completion_percentage": 100.0,
        }
        study_hours = 12.0

        html_out = build_subject_card_html(subject, progress, study_hours)

        assert "Operating Systems" in html_out
        assert "CS302" in html_out
        assert "4/4 Topics" in html_out
        assert "100%" in html_out
        assert "Completed" in html_out
        assert "style=\"width: 100.0%;\"" in html_out

    def test_subject_without_study_sessions(self):
        """Scenario 5: Subject without study sessions displays 0.0 hrs."""
        subject = {"id": 6, "subject_name": "Linear Algebra", "subject_code": "MA201"}
        progress = {"total_topics": 3, "completed_topics": 0}
        study_hours = 0.0

        html_out = build_subject_card_html(subject, progress, study_hours)

        assert "Linear Algebra" in html_out
        assert "0/3 Topics" in html_out
        assert "0.0 hrs" in html_out

    def test_multiple_subject_cards_rendered_in_dashboard(self):
        """Scenario 6: Multiple subject cards rendered in batch without cross-interference."""
        subjects = [
            {"id": 2, "subject_name": "DS", "subject_code": "VS101"},
            {"id": 3, "subject_name": "Dsa", "subject_code": "BD101"},
            {"id": 4, "subject_name": "coa", "subject_code": None},
        ]
        progs = [
            {"total_topics": 2, "completed_topics": 0},
            {"total_topics": 2, "completed_topics": 1},
            {"total_topics": 0, "completed_topics": 0},
        ]
        hours = [1.0, 3.0, 0.0]

        outputs = [
            build_subject_card_html(s, p, h)
            for s, p, h in zip(subjects, progs, hours)
        ]

        assert len(outputs) == 3
        # Ensure none have markdown code block indents (no lines starting with 4+ spaces)
        for out in outputs:
            for line in out.splitlines():
                assert not line.startswith("    "), f"Indented line detected that could trigger code block: {line!r}"

    def test_subject_names_with_special_html_characters(self):
        """Scenario 7: Subject names containing special HTML characters are safely escaped."""
        subject = {
            "id": 99,
            "subject_name": "<Script>alert('XSS')</Script> & Algorithms \"Pro\"",
            "subject_code": "<C&D>",
        }
        progress = {"total_topics": 1, "completed_topics": 1}

        html_out = build_subject_card_html(subject, progress, 2.5)

        assert "<Script>" not in html_out
        assert "&lt;Script&gt;alert(&#x27;XSS&#x27;)&lt;/Script&gt; &amp; Algorithms &quot;Pro&quot;" in html_out
        assert "&lt;C&amp;D&gt;" in html_out

    def test_render_subject_card_calls_streamlit_html_or_markdown(self):
        """Verify render_subject_card uses st.html or st.markdown with unsafe_allow_html=True."""
        subject = {"id": 2, "subject_name": "DS", "subject_code": "VS101"}
        progress = {"total_topics": 2, "completed_topics": 0}

        import streamlit as st
        with patch.object(st, "html", create=True) as mock_html:
            render_subject_card(subject, progress, 1.0)
            mock_html.assert_called_once()
            args, _ = mock_html.call_args
            assert "DS" in args[0]
            assert "VS101" in args[0]
