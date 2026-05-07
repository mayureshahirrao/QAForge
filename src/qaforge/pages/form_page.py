"""
qaforge.pages.form_page
=======================
Demonstrates: form fields, dropdowns, checkboxes, file upload/download,
iframes, and download interception.
"""
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import Locator, FrameLocator
from qaforge.pages.base_page import BasePage


class FormPage(BasePage):
    URL_PATH = "/forms/new"

    # ---- locators ----
    @property
    def title_input(self) -> Locator:
        return self.page.get_by_label("Title")

    @property
    def description_input(self) -> Locator:
        return self.page.get_by_label("Description")

    @property
    def category_select(self) -> Locator:
        return self.page.get_by_label("Category")

    @property
    def agree_checkbox(self) -> Locator:
        return self.page.get_by_role("checkbox", name="I agree to the terms")

    @property
    def attachment_input(self) -> Locator:
        return self.page.locator("input[type='file']")

    @property
    def captcha_frame(self) -> FrameLocator:
        return self.page.frame_locator("iframe[title='captcha']")

    @property
    def submit_btn(self) -> Locator:
        return self.page.get_by_role("button", name="Submit")

    @property
    def success_toast(self) -> Locator:
        return self.page.get_by_test_id("toast-success")

    @property
    def export_btn(self) -> Locator:
        return self.page.get_by_role("button", name="Export PDF")

    # ---- actions ----
    def fill_form(self, title: str, description: str, category: str, attachment: Path) -> None:
        self.title_input.fill(title)
        self.description_input.fill(description)
        self.category_select.select_option(label=category)
        self.attachment_input.set_input_files(str(attachment))
        self.agree_checkbox.check()

    def confirm_in_iframe(self) -> None:
        # Demonstrates frame interaction
        self.captcha_frame.get_by_role("checkbox", name="I'm not a robot").check()

    def submit(self) -> None:
        self.submit_btn.click()
        self.expect_visible(self.success_toast, timeout_ms=15000)

    def export_pdf(self, save_to: Path) -> Path:
        with self.page.expect_download() as dl_info:
            self.export_btn.click()
        download = dl_info.value
        save_to.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(save_to))
        return save_to
