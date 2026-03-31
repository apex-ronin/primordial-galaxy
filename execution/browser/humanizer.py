import asyncio
import random
from playwright.async_api import Page

async def human_move(page: Page, x: float, y: float):
    """Moves mouse in a non-linear path with jitter to simulate human movement."""
    current_mouse = await page.evaluate("() => ({ x: window.scrollX + window.innerWidth / 2, y: window.scrollY + window.innerHeight / 2 })") # Fallback estimate
    # Simple jittered movement
    steps = random.randint(5, 12)
    for _ in range(steps):
        jitter_x = x + random.uniform(-3, 3)
        jitter_y = y + random.uniform(-3, 3)
        await page.mouse.move(jitter_x, jitter_y)
        await asyncio.sleep(random.uniform(0.01, 0.04))

async def human_click(page: Page, selector: str):
    """Finds an element and clicks it like a human (moves to it first, random point, delay)."""
    element = await page.wait_for_selector(selector, state="visible", timeout=10000)
    box = await element.bounding_box()
    if not box:
        print(f"--- Warning: Element {selector} has no bounding box. Simple click fallback. ---")
        await element.click()
        return

    # Random target point within the element
    target_x = box['x'] + random.uniform(2, box['width'] - 2)
    target_y = box['y'] + random.uniform(2, box['height'] - 2)

    await human_move(page, target_x, target_y)
    await asyncio.sleep(random.uniform(0.1, 0.5))  # Reflex delay
    await page.mouse.click(target_x, target_y)
    print(f"--- Human Click: {selector} ---")

async def human_type(page: Page, selector: str, text: str):
    """Types text with variable speeds and pauses."""
    await page.focus(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.04, 0.18))
        if char in ['.', ' ', ',']:
            await asyncio.sleep(random.uniform(0.2, 0.6))  # Pausing at intervals
    print(f"--- Human Type: {selector} ---")

async def human_scroll(page: Page):
    """Natural, irregular scrolling."""
    distance = random.randint(100, 400)
    steps = random.randint(3, 7)
    for _ in range(steps):
        await page.mouse.wheel(0, distance / steps)
        await asyncio.sleep(random.uniform(0.05, 0.2))
    print(f"--- Human Scroll ---")
