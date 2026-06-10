import json
from doc_fetcher import get_document_text
from gemini_analyst import analyze_rfp

def analyze_opportunity(opportunity):
    """
    Analyzes an opportunity using AI when possible, falls back to keywords.
    """
    title = opportunity['title'].lower()
    link = opportunity['link']
    
    # 1. Get Content — title + snippet seed, upgraded with full document text.
    # Item 3.4 (2026-06-09): non-PDF links (CSDA posting pages) now get the page
    # text + linked RFP documents pulled, so red-team/antibody work from full
    # text instead of title+snippet.
    snippet = opportunity.get('snippet', '')
    full_text = (title + " " + snippet).strip()
    pdf_status = "No PDF"

    print(f"    [Brain] Fetching documents for: {title[:40]}...")
    text, status = get_document_text(link)
    pdf_status = status
    if text:
        full_text = f"{title}\n{snippet}\n\n{text}"

    # 2. Try AI Analysis (if we have content)
    # 2026-06-09 fix: the old >100-char gate silently dropped short-title records
    # (terse SAM.gov titles, snippet-less CSDA postings) to keyword scoring while
    # labeling them "AI unavailable". Local tier is free — analyze anything with
    # enough text to carry signal.
    ai_analysis = None
    fallback_reason = "content too short"
    if len(full_text) > 20:
        ai_analysis = analyze_rfp(full_text)
        fallback_reason = "AI unavailable"
    if ai_analysis and ai_analysis.get("status") == "rejected":
        ai_analysis = None
        fallback_reason = "cost cap exceeded"

    # 3. Determine Score
    if ai_analysis:
        # Use AI score
        score = ai_analysis.get('win_probability', 50)
        fit_label = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
        
        # Enrich opportunity with AI insights
        opportunity['win_probability'] = score
        opportunity['fit_label'] = fit_label
        opportunity['pdf_status'] = pdf_status
        opportunity['project_type'] = ai_analysis.get('project_type', 'Unknown')
        opportunity['remote_friendly'] = ai_analysis.get('remote_friendly', False)
        opportunity['small_business_setaside'] = ai_analysis.get('small_business_setaside', False)
        opportunity['estimated_value'] = ai_analysis.get('estimated_value', 'Not Specified')
        opportunity['strategic_notes'] = ai_analysis.get('strategic_reasoning', '')
        
        # New: Red Team & Immune System
        opportunity['red_team'] = ai_analysis.get('red_team_findings', {})
        opportunity['immune_system'] = ai_analysis.get('immune_system_antibody', {})
        
        opportunity['analysis_method'] = f"LLM Dual-Track [{ai_analysis.pop('_llm_provider', 'unknown')}]"
    else:
        # Fallback to keyword analysis
        score = keyword_score(title)
        fit_label = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
        
        opportunity['win_probability'] = score
        opportunity['fit_label'] = fit_label
        opportunity['pdf_status'] = pdf_status
        opportunity['analysis_notes'] = f"Keyword-based analysis ({fallback_reason})"
        opportunity['analysis_method'] = "Keywords"
    
    return opportunity

def keyword_score(title):
    """Fallback keyword-based scoring."""
    high_value_keywords = [
        "study", "plan", "design", "consulting", "update", 
        "analysis", "software", "system", "support", "services",
        "outreach", "legal", "audit", "engineering", "architect"
    ]
    
    low_value_keywords = [
        "construction", "paving", "replacement", "repair", 
        "concrete", "asphalt", "fencing", "painting", "vehicle",
        "equipment", "generator", "pump", "janitorial", "mowing"
    ]
    
    score = 50
    for word in high_value_keywords:
        if word in title:
            score += 15
    for word in low_value_keywords:
        if word in title:
            score -= 20
    
    return max(0, min(100, score))

if __name__ == "__main__":
    # Test
    test_opp = {"title": "Design & Construction Standards Update", "link": "http://example.com"}
    print(json.dumps(analyze_opportunity(test_opp), indent=2))
