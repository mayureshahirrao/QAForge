"""
qaforge.pages.login_page
========================
Login page for the Next.js frontend. Demonstrates locators, fill, click,
network capture, and assertions.
"""
from __future__ import annotations

from playwright.sync_api import Locator

from qaforge.pages.base_page import BasePage


class LoginPage(BasePage):
    URL_PATH = "/login"

    # ---- locators (Playwright recommends role/label-based locators) ----
    @property
    def email_input(self) -> Locator:
        return self.page.get_by_label("Email")

    @property
    def password_input(self) -> Locator:
        return self.page.get_by_label("Password")

    @property
    def otp_input(self) -> Locator:
        return self.page.get_by_label("One-time code")

    @property
    def submit_btn(self) -> Locator:
        return self.page.get_by_role("button", name="Sign in")

    @property
    def error_banner(self) -> Locator:
        return self.page.get_by_test_id("login-error")

    # ---- actions ----
    def login(self, email: str, password: str, otp: str | None = None) -> None:
        self.email_input.fill(email)
        self.password_input.fill(password)
        if otp:
            self.otp_input.fill(otp)
        # capture the auth response while clicking submit
        with self.page.expect_response(lambda r: "/auth/login" in r.url) as resp_info:
            self.submit_btn.click()
        resp = resp_info.value
        assert resp.ok, f"Login API failed: {resp.status} {resp.text()}"

    def expect_login_failed(self, message: str) -> None:
        self.expect_visible(self.error_banner)
        self.expect_text(self.error_banner, message)
