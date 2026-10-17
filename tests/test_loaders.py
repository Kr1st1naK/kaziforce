"""Text cleaning in kaziforce_api.data.loaders."""

import numpy as np
import pytest

from kaziforce_api.data.loaders import clean_profile_text


def test_lowercases_mostly_uppercase_text_and_joins_lines():
    raw = "SUMMARY\nTHE SR. HR GENERALIST PROVIDES HR EXPERTISE.\n\n• ANALYZE HR DATA"
    assert clean_profile_text(raw) == "summary the sr. hr generalist provides hr expertise. analyze hr data"


def test_keeps_case_of_normal_text():
    assert clean_profile_text("Fundi wa umeme in Nairobi, 5 years.") == "Fundi wa umeme in Nairobi, 5 years."


@pytest.mark.parametrize("contact", [
    "jobs@example.com",
    "first.last+hr@mail.example.co.ke",
    "(555) 123-4567",
    "555-123-4567",
    "+1 555.123.4567",
    "0712345678",
    "https://careers.example.com/apply",
    "www.example.org/jobs",
])
def test_removes_contact_details(contact):
    out = clean_profile_text(f"Apply now: {contact} today")
    assert out == "Apply now: today"


def test_keeps_salaries_dates_and_ordinary_numbers():
    text = "Pay $85,000 - $95,000 from 2024-10-01, 40 hours, 3 years"
    assert clean_profile_text(text) == text


def test_missing_and_empty_values_give_empty_string():
    assert clean_profile_text(None) == ""
    assert clean_profile_text(np.nan) == ""
    assert clean_profile_text("   ") == ""


def test_html_and_bullets_are_removed():
    assert clean_profile_text("<p>Install sockets</p>\uf0b7 Fix lights") == "Install sockets Fix lights"


@pytest.mark.parametrize("handle", ["@acmecareers", "careers@acme", "@acme.com", "hr@ "])
def test_removes_handles_and_partial_emails(handle):
    assert "@" not in clean_profile_text(f"Follow {handle} for jobs")


def test_keeps_a_lone_at_sign():
    assert clean_profile_text("Starts @ 325 Main St") == "Starts @ 325 Main St"
