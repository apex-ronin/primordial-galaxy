import json
from playwright.async_api import Page, Frame

async def parse_frame_state(frame: Frame):
    """Extracts interactive state from a given frame/iframe context."""
    extraction_script = """
    () => {
        const interactives = [];
        const elements = document.querySelectorAll('button, a, input, select, textarea, [role="button"], img[id*="choice"], div[class*="choice"]');

        elements.forEach((el, index) => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).display !== 'none') {
                interactives.push({
                    id: el.id || `el-${index}`,
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText || el.value || el.placeholder || el.ariaLabel || 'No Label',
                    type: el.type || 'N/A',
                    selector: el.id ? `#${el.id}` : el.className ? `.${el.className.split(' ')[0]}` : el.tagName.toLowerCase(),
                    href: el.href || null,
                    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                });
            }
        });
        return interactives;
    }
    """
    try:
        elements = await frame.evaluate(extraction_script)
        return elements
    except:
        return []

async def parse_page_state(page: Page):
    """Recursively extracts interactive state from main page and all detectible iframes."""
    main_elements = await parse_frame_state(page.main_frame)

    all_elements = main_elements
    for frame in page.frames:
        if frame != page.main_frame:
            frame_elements = await parse_frame_state(frame)
            if frame_elements:
                print(f"--- Perception: Found interactive content inside iframe: {frame.url[:50]}... ---")
                all_elements.extend(frame_elements)

    return {
        "title": await page.title(),
        "url": page.url,
        "elements": all_elements
    }
