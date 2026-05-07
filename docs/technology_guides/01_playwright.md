# 01 — Playwright (UI Automation)

> **Used in QAForge:** ✅ Always — it is the UI engine.
> **Source files:** `src/qaforge/core/browser_factory.py`, `src/qaforge/pages/*.py`, `src/qaforge/utils/network.py`, `features/steps/ui_steps.py`.

---

## 1. Why Playwright (vs Selenium/Cypress)

- **Auto-waiting** — actions and `expect()` retry until the locator is actionable; eliminates 90% of `time.sleep` flakiness.
- **One API for Chromium, Firefox, WebKit** — same code, three engines.
- **Tracing + video + screenshot** built in — invaluable for CI debugging.
- **Network interception** is first-class (no proxy hacks).
- **Parallel-safe** — each `BrowserContext` is isolated like an incognito window.

---

## 2. Setup

```bash
pip install playwright==1.48.0
playwright install --with-deps chromium firefox webkit
```

In QAForge, `BrowserFactory` (in `core/browser_factory.py`) is the **only** code that calls `sync_playwright()`. Step authors use the `context.page` provisioned by `before_scenario`.

---

## 3. Command catalogue (with QAForge usage indicators)

✅ = used directly somewhere in QAForge. ☑ = available; not currently used but supported by the design.

### 3.1  Navigation

| Command                                      | Purpose                                       | Status |
| -------------------------------------------- | --------------------------------------------- | ------ |
| `page.goto(url, wait_until=...)`             | Navigate to URL.                              | ✅ `BasePage.open` |
| `page.reload()`                              | Reload the current page.                      | ✅ `BasePage.reload` |
| `page.go_back()` / `page.go_forward()`       | Browser history.                              | ☑      |
| `page.wait_for_url(pattern)`                 | Wait until URL matches pattern.               | ☑ (use `expect(page).to_have_url`) |
| `page.set_default_timeout(ms)`               | Default action timeout.                       | ✅ `BrowserFactory.new_context` |
| `page.set_default_navigation_timeout(ms)`    | Navigation timeout.                           | ✅ `BrowserFactory.new_context` |

### 3.2  Locators (the right way)

Prefer **role-based** and **label-based** locators — they survive DOM refactors.

| Command                                        | Notes                                | Status |
| ---------------------------------------------- | ------------------------------------ | ------ |
| `page.get_by_role(role, name=)`                | The default — accessibility-aware.   | ✅     |
| `page.get_by_label(text)`                      | Form fields with `<label>`.          | ✅     |
| `page.get_by_test_id(id)`                      | Use for non-semantic UI markers.     | ✅     |
| `page.get_by_text(text, exact=)`               | Last resort for static text.         | ☑     |
| `page.get_by_placeholder(text)`                | Inputs without labels.               | ☑     |
| `page.get_by_alt_text(text)`                   | `<img alt=>`                         | ☑     |
| `page.get_by_title(text)`                      | `[title]` attributes.                | ☑     |
| `page.locator(css_or_xpath)`                   | Fallback to selectors.               | ✅ (file inputs only)|
| `locator.filter(has_text=, has=)`              | Narrow within a list.                | ☑     |
| `locator.first` / `last` / `nth(i)`            | Index into matches.                  | ☑     |

### 3.3  Actions

| Command                                       | Purpose                                | Status |
| --------------------------------------------- | -------------------------------------- | ------ |
| `locator.click(button=, modifiers=, force=)`  | Click; auto-waits for actionability.   | ✅     |
| `locator.dblclick()`                          | Double-click.                          | ☑     |
| `locator.fill(value)`                         | Set the value of an input.             | ✅     |
| `locator.type(text, delay=)`                  | Send keystrokes one at a time.         | ☑     |
| `locator.press(key)`                          | Single key (`"Enter"`, `"Control+A"`). | ☑     |
| `locator.check()` / `uncheck()`               | Checkboxes and radios.                 | ✅ form |
| `locator.select_option(value=, label=)`       | Native `<select>`.                     | ✅ form |
| `locator.set_input_files(paths)`              | File upload.                           | ✅ form |
| `locator.hover()`                             | Mouse hover.                           | ☑     |
| `locator.focus()` / `blur()`                  | Focus management.                      | ☑     |
| `locator.drag_to(target)`                     | Drag & drop.                           | ☑     |
| `locator.scroll_into_view_if_needed()`        | Scroll-then-act.                       | ☑     |

### 3.4  Assertions (`from playwright.sync_api import expect`)

All `expect()` calls auto-retry until timeout — never wrap them in custom retry loops.

| Assertion                                          | Status |
| -------------------------------------------------- | ------ |
| `expect(locator).to_be_visible()`                  | ✅ `BasePage.expect_visible` |
| `expect(locator).to_be_hidden()`                   | ☑     |
| `expect(locator).to_be_enabled()` / `disabled()`   | ☑     |
| `expect(locator).to_be_checked()`                  | ☑     |
| `expect(locator).to_have_text(text)`               | ☑     |
| `expect(locator).to_contain_text(text)`            | ✅ `BasePage.expect_text` |
| `expect(locator).to_have_value(value)`             | ☑     |
| `expect(locator).to_have_attribute(name, value)`   | ☑     |
| `expect(locator).to_have_count(n)`                 | ☑     |
| `expect(page).to_have_url(pattern)`                | ✅ `BasePage.expect_url`, `DashboardPage.open_settings` |
| `expect(page).to_have_title(title)`                | ☑     |

### 3.5  Waits (rarely needed — auto-waiting first)

| Command                                          | When to use                              | Status |
| ------------------------------------------------ | ---------------------------------------- | ------ |
| `page.wait_for_load_state("networkidle")`        | After dashboards finish loading widgets. | ☑     |
| `page.wait_for_selector(selector)`               | Legacy code; prefer `locator.first`.     | ☑     |
| `page.wait_for_response(predicate)`              | When asserting after a click.            | ☑     |
| `page.expect_response(predicate)`                | Wraps action + capture.                  | ✅ `LoginPage.login` |
| `page.expect_request(predicate)`                 | Same for outgoing requests.              | ☑     |
| `page.expect_download()`                         | Capture a download.                      | ✅ `FormPage.export_pdf` |
| `page.expect_popup()`                            | Capture a `window.open`.                 | ☑     |

### 3.6  Frames

| Command                                    | Status |
| ------------------------------------------ | ------ |
| `page.frame_locator(selector)`             | ✅ `FormPage.captcha_frame` |
| `page.frames`                              | ☑     |
| `page.frame(name=)` / `frame(url=)`        | ☑     |

### 3.7  Files: upload & download

| Command                                               | Status |
| ----------------------------------------------------- | ------ |
| `locator.set_input_files(paths)`                      | ✅ form upload |
| `page.expect_download()` → `download.save_as(path)`   | ✅ form export |
| `page.expect_file_chooser()` (non-`<input>` triggers) | ☑     |

### 3.8  Network interception

| Command                                       | Purpose                                 | Status |
| --------------------------------------------- | --------------------------------------- | ------ |
| `page.on("request", handler)`                 | Record outgoing requests.               | ✅ `NetworkRecorder` |
| `page.on("response", handler)`                | Inspect responses.                      | ☑     |
| `page.route(url_glob, handler)` + `route.fulfill` | Stub responses.                     | ✅ `stub_route` |
| `route.continue_(headers=, post_data=)`       | Modify in flight.                       | ✅ `block_third_party` |
| `route.abort(error_code=)`                    | Block specific requests.                | ✅ `block_third_party` |
| `page.unroute(url_glob)`                      | Remove a route.                         | ☑     |

### 3.9  Browser contexts

| Command                                     | Purpose                                                | Status |
| ------------------------------------------- | ------------------------------------------------------ | ------ |
| `browser.new_context(viewport=, locale=, timezone_id=, ignore_https_errors=, record_video_dir=, record_video_size=, storage_state=)` | Isolated session per scenario. | ✅ `BrowserFactory.new_context` |
| `context.tracing.start(screenshots=, snapshots=, sources=)` / `tracing.stop(path=)` | Capture trace zip. | ✅ |
| `context.storage_state(path=)`              | Persist auth cookies between scenarios.                | ☑     |
| `context.add_cookies([...])`                | Inject cookies.                                        | ☑     |
| `context.grant_permissions([...], origin=)` | Geolocation, notifications, etc.                       | ☑     |
| `context.set_geolocation({lat, longitude})` | Mock GPS.                                              | ☑     |
| `context.set_offline(True)`                 | Simulate offline.                                      | ☑     |
| `context.new_cdp_session(page)`             | Raw Chrome DevTools Protocol.                          | ☑     |

### 3.10  Diagnostics

| Command                                   | Status |
| ----------------------------------------- | ------ |
| `page.screenshot(path=, full_page=)`      | ✅ `after_step` on failure |
| `page.video.path()`                       | ✅ attached to Allure on failure |
| `context.tracing.stop(path=)`             | ✅ trace zip on failure |
| `page.on("console", handler)`             | ☑     |
| `page.on("pageerror", handler)`           | ☑     |
| `page.evaluate("() => ...")`              | Run JS in page.   | ☑     |

---

## 4. QAForge usage cheatsheet

```python
# Inside a step (`features/steps/ui_steps.py`)
from playwright.sync_api import expect
from qaforge.pages.login_page import LoginPage

login = LoginPage(context.page, context.cfg.ui.base_url)
login.open()
login.login("alice@example.com", "Sup3r$ecret!")
expect(context.page).to_have_url("**/dashboard")
```

```python
# Network stub
from qaforge.utils.network import stub_route
stub_route(context.page, "**/api/metrics**", status=200, json_body={"users": 100})
```

---

## 5. Common pitfalls

- **Don't `time.sleep()`.** Use `expect(...)` — it auto-retries.
- **Don't query DOM directly with `page.locator("//div[3]")`.** That tightly couples tests to layout. Use `get_by_role`/`get_by_label`/`get_by_test_id`.
- **Don't reuse a context across scenarios.** Each scenario gets a fresh one in `before_scenario` — that's how QAForge stays parallel-safe.
- **Don't manually capture screenshots in steps.** `after_step` does it on failure. Adding manual ones bloats the report.

---

## 6. Tracing — the killer feature

When a CI failure is opaque, open the Playwright trace:

```bash
playwright show-trace reports/traces/<scenario>.zip
```

You get: a timeline of every action, screenshots before/after, console logs, network calls, and the DOM at each step. This single feature pays for the framework switch.
