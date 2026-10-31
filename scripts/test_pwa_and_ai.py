"""Browser verification test for Knowledge-Grounded AI Fallback, PWA, and Desktop Download."""
import sys
import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\Rupesh\.gemini\antigravity\brain\01d82a95-296f-4782-849b-ef86aedacde1"

def run_tests():
    with sync_playwright() as p:
        # Launch using installed Microsoft Edge
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("1. Navigating to http://127.0.0.1:8000 ...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # ── Test 1: Ask 'where can i study' ──────────────────────────────────
        print("2. Testing student query: 'where can i study' ...")
        page.fill("#q", "where can i study")
        page.press("#q", "Enter")

        # Wait for AI answer card
        page.wait_for_selector(".card-a", timeout=15000)
        time.sleep(1.5)

        # Check for AI watermark pill
        ai_pill = page.query_selector(".pill.ai")
        assert ai_pill is not None, "AI watermark pill (.pill.ai) not found!"
        print("   Found AI watermark pill:", ai_pill.inner_text().encode("ascii", "replace").decode())

        ans_el = page.query_selector(".card-a .ans")
        ans_text = ans_el.inner_text() if ans_el else ""
        print("   AI Answer snippet:", ans_text[:120].encode("ascii", "replace").decode(), "...")

        study_screenshot = os.path.join(ARTIFACT_DIR, "proof_ai_study_answer.png")
        page.screenshot(path=study_screenshot)
        print(f"   Saved screenshot: {study_screenshot}")

        # ── Test 2: Verify PWA + Desktop Download in Sidebar ───────
        print("3. Testing sidebar with PWA and Desktop (.exe) download ...")
        dl_btn = page.query_selector("#dl-win-btn")
        assert dl_btn is not None, "Download Windows App button not found!"
        print("   Found Windows App download button href:", dl_btn.get_attribute("href"))

        pwa_btn = page.query_selector("#pwa-install-btn")
        assert pwa_btn is not None, "PWA install button element not found in sidebar!"
        print("   Found PWA install button in sidebar!")

        sidebar_screenshot = os.path.join(ARTIFACT_DIR, "proof_pwa_and_desktop_download.png")
        page.screenshot(path=sidebar_screenshot)
        print(f"   Saved screenshot: {sidebar_screenshot}")

        # ── Test 3: Mobile Viewport Layout Verification ───────────────────────
        print("4. Testing Mobile Viewport (iPhone 14 / Android) ...")
        mobile_page = context.new_page()
        mobile_page.set_viewport_size({"width": 390, "height": 844})
        mobile_page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # Open hamburger drawer on mobile
        mobile_page.click("#hamb")
        mobile_page.wait_for_selector("#side.open", timeout=5000)
        time.sleep(0.5)

        mobile_drawer_screenshot = os.path.join(ARTIFACT_DIR, "proof_mobile_drawer_pwa.png")
        mobile_page.screenshot(path=mobile_drawer_screenshot)
        print(f"   Saved mobile drawer screenshot: {mobile_drawer_screenshot}")

        # Close drawer and ask question
        mobile_page.evaluate("side(false)")
        time.sleep(0.5)
        mobile_page.fill("#q", "where can i study")
        mobile_page.press("#q", "Enter")
        mobile_page.wait_for_selector(".card-a", timeout=15000)
        time.sleep(1.0)

        mobile_screenshot = os.path.join(ARTIFACT_DIR, "proof_mobile_pwa_experience.png")
        mobile_page.screenshot(path=mobile_screenshot)
        print(f"   Saved mobile screenshot: {mobile_screenshot}")

        browser.close()
        print("\nAll browser verification tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()
