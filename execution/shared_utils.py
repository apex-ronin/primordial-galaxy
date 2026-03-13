def antibody_prompt_sanitizer_v1(text):
    """
    Finding AS-01 (Grok Council): Prevents 'Prompt Kiddie' injection vectors by 
    stripping potentially malicious command structures before LLM analysis.
    """
    if not isinstance(text, str):
        return ""
    forbidden = ["IGNORE ALL PREVIOUS", "SYSTEM PROMPT", "DEVELOPER MODE"]
    for word in forbidden:
        text = text.replace(word, f"[REDACTED_{word.replace(' ', '_')}]")
    return text

def calculate_roi_safe(payout, cost):
    """
    Finding AS-02: Prevents ZeroDivisionError and handled non-numeric inputs.
    Returns a safe ROI multiplier.
    """
    try:
        payout = float(payout)
        cost = float(cost)
        if cost <= 0:
            return 999.0 # "Infinite" ROI for negligible cost
        return round(payout / cost, 2)
    except (ValueError, TypeError):
        return 0.0
