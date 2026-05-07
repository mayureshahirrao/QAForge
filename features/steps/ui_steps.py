"""
features/steps/ui_steps.py
==========================
Step definitions for UI scenarios. Demonstrates Playwright commands:
navigation, locators, fill, click, expect, downloads, frames, network.
"""
from pathlib import Path

from behave import given, then, when
from playwright.sync_api import expect

from qaforge.pages.dashboard_page import DashboardPage
from qaforge.pages.form_page import FormPage
from qaforge.pages.login_page import LoginPage
from qaforge.utils.network import NetworkRecorder, stub_route

ROOT = Path(__file__).resolve().parents[2]


# ---------- navigation ----------
@given('I open the login page')
def step_open_login(context):
    context.login_page = LoginPage(context.page, context.cfg.ui.base_url)
    context.login_page.open()


@given('I open the form page')
def step_open_form(context):
    context.form_page = FormPage(context.page, context.cfg.ui.base_url)
    context.form_page.open()


# ---------- login ----------
@when('I log in as "{key}"')
def step_login_as(context, key):
    user = context.user if hasattr(context, "user") and context.user.get("key") == key else None
    if user is None:
        from qaforge.data.loaders import static_user
        user = static_user(key)
    context.login_page.login(
        email=user["email"], password=user["password"], otp=user.get("otp")
    )


@when('I log in with email "{email}" and password "{password}"')
def step_login_creds(context, email, password):
    context.login_page.login(email, password)


@then('I should land on the dashboard as "{email}"')
def step_dashboard_check(context, email):
    dash = DashboardPage(context.page, context.cfg.ui.base_url)
    dash.expect_url("**/dashboard", timeout_ms=15000)
    dash.expect_logged_in_as(email)


@then('I should see the login error "{message}"')
def step_login_error(context, message):
    context.login_page.expect_login_failed(message)


# ---------- form ----------
@when('I fill the form with title "{title}", description "{desc}", category "{cat}", attachment "{rel_path}"')
def step_fill_form(context, title, desc, cat, rel_path):
    context.form_page.fill_form(title, desc, cat, ROOT / rel_path)


@when('I confirm the captcha checkbox')
def step_captcha(context):
    context.form_page.confirm_in_iframe()


@when('I submit the form')
def step_submit_form(context):
    context.form_page.submit()


@then('a success toast should be visible')
def step_toast(context):
    expect(context.form_page.success_toast).to_be_visible()


@when('I export the form as PDF to "{rel_path}"')
def step_export(context, rel_path):
    out = ROOT / rel_path
    context.form_page.export_pdf(out)
    context.exported_file = out


@then('the exported file should exist and be non-empty')
def step_exported(context):
    assert context.exported_file.exists() and context.exported_file.stat().st_size > 0


# ---------- network ----------
@given('I record all network requests')
def step_record(context):
    context.network_recorder = NetworkRecorder(context.page)


@given('I stub the endpoint "{url_glob}" with status {status:d} and JSON body')
def step_stub(context, url_glob, status):
    import json as _json
    body = _json.loads(context.text)
    stub_route(context.page, url_glob, status=status, json_body=body)


@then('a request to "{path_substr}" should have been made')
def step_assert_request(context, path_substr):
    matches = context.network_recorder.filter(lambda r: path_substr in r.url)
    assert matches, (
        f"No request containing '{path_substr}' captured. "
        f"Saw: {[r.url for r in context.network_recorder.requests][:10]}"
    )
