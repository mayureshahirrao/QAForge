"""qaforge.pages.dashboard_page — landing page after login."""
from __future__ import annotations
from playwright.sync_api import Locator
from qaforge.pages.base_page import BasePage


class DashboardPage(BasePage):
    URL_PATH = "/dashboard"

    @property
    def welcome_header(self) -> Locator:
        return self.page.get_by_role("heading", name="Welcome")

    @property
    def user_menu(self) -> Locator:
        return self.page.get_by_test_id("user-menu")

    @property
    def nav_settings(self) -> Locator:
        return self.page.get_by_role("link", name="Settings")

    def open_settings(self) -> None:
        self.nav_settings.click()
        self.expect_url("**/settings", timeout_ms=15000)

    def expect_logged_in_as(self, email: str) -> None:
        self.expect_visible(self.user_menu)
        self.expect_text(self.user_menu, email)
