import json
from pdf_reader import get_pdf_text
from gemini_analyst import analyze_rfp

def analyze_opportunity(opportunity):
    """
    Analyzes an opportunity using AI when possible, falls back to keywords.
    """
    title = opportunity['title'].lower()
    link = opportunity['link']
    
    # 1. Get Content (Title + PDF Text if available)
    # Bug 6 fix: seed full_text with title + snippet so non-PDF sources exceed the
    # 100-char threshold and get AI analysis instead of falling back to keywords.
    snippet = opportunity.get('snippet', '')
    full_text = (title + " " + snippet).strip()
    pdf_status = "No PDF"

    if link.lower().endswith('.pdf'):
        print(f"    [Brain] Downloading PDF for analysis: {title[:30]}...")
        text, error = get_pdf_text(link)
        if text:
            full_text = text  # Full PDF text always wins
            pdf_status = "PDF Analyzed"
        else:
            pdf_status = f"PDF Error: {error}"

    # 2. Try AI Analysis (if we have content)
    ai_analysis = None
    if len(full_text) > 100:  # Only worth sending to AI if we have real content
        ai_analysis = analyze_rfp(full_text)
    
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
        
        opportunity['analysis_method'] = "Gemini AI (Dual-Track)"
    else:
        # Fallback to keyword analysis
        score = keyword_score(title)
        fit_label = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
        
        opportunity['win_probability'] = score
        opportunity['fit_label'] = fit_label
        opportunity['pdf_status'] = pdf_status
        opportunity['analysis_notes'] = "Keyword-based analysis (AI unavailable)"
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
