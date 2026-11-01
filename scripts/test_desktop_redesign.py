"""Verification test for Desktop UI Redesign, App Logo, and Platform Visibility."""
import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\Rupesh\.gemini\antigravity\brain\01d82a95-296f-4782-849b-ef86aedacde1"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # ── Test 1: Standard Web View (e.g. Vercel deployment) ───────────────
        print("1. Testing Web view (Vercel / Browser) ...")
        context_web = browser.new_context(viewport={"width": 1280, "height": 800})
        page_web = context_web.new_page()
        page_web.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # Verify logo in sidebar
        logo_img = page_web.query_selector(".logo img.mark")
        assert logo_img is not None, "Sidebar logo image (.logo img.mark) not found!"
        print("   Sidebar logo source:", logo_img.get_attribute("src"))

        # Verify buttons ARE visible on Web
        pwa_btn = page_web.query_selector("#pwa-install-btn")
        dl_btn = page_web.query_selector("#dl-win-btn")
        assert dl_btn is not None and dl_btn.is_visible(), "Download Windows App button should be visible on Web!"
        print("   Web view correctly displays download button:", dl_btn.is_visible())

        screenshot_web = os.path.join(ARTIFACT_DIR, "proof_web_with_logo_and_buttons.png")
        page_web.screenshot(path=screenshot_web)
        print(f"   Saved Web view screenshot: {screenshot_web}")

        # ── Test 2: Electron Desktop App Simulation ──────────────────────────
        print("2. Testing Electron Desktop App view ...")
        context_electron = browser.new_context(viewport={"width": 1280, "height": 800})
        page_electron = context_electron.new_page()
        # Inject electronAPI context bridge before document loads
        page_electron.add_init_script("""
            window.electronAPI = {
                isElectron: true,
                platform: 'win32',
                version: '1.0.0',
                reload: () => console.log('electron reload'),
                toggleFullscreen: () => console.log('electron fullscreen')
            };
        """)
        page_electron.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # Verify is-electron class is applied to root
        is_electron_class = page_electron.evaluate("document.documentElement.classList.contains('is-electron')")
        assert is_electron_class, "Class 'is-electron' should be added to <html> in Electron!"
        print("   'is-electron' class active:", is_electron_class)

        # Verify install and download buttons are HIDDEN
        pwa_vis = page_electron.is_visible("#pwa-install-btn")
        dl_vis = page_electron.is_visible("#dl-win-btn")
        assert not pwa_vis, "PWA install button should be HIDDEN in Electron!"
        assert not dl_vis, "Windows App download button should be HIDDEN in Electron!"
        print("   PWA button visible in Electron:", pwa_vis, "(Expected: False)")
        print("   Windows download button visible in Electron:", dl_vis, "(Expected: False)")

        # Verify in-app desktop menu button exists and opens
        menu_btn = page_electron.query_selector("#app-menu-btn")
        assert menu_btn is not None, "App menu button (#app-menu-btn) not found!"
        page_electron.click("#app-menu-btn")
        time.sleep(0.3)
        menu_dropdown_vis = page_electron.is_visible("#app-menu-dropdown")
        assert menu_dropdown_vis, "App menu dropdown should be visible when clicked!"
        print("   In-app menu dropdown opened successfully!")

        screenshot_electron = os.path.join(ARTIFACT_DIR, "proof_desktop_electron_ui.png")
        page_electron.screenshot(path=screenshot_electron)
        print(f"   Saved Electron view screenshot: {screenshot_electron}")

        browser.close()
        print("\nAll Desktop & Web platform tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()
