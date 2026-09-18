from playwright.sync_api import Page

from automation_infra.core.web.pages.base_page import BasePage


class BaseAuthPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input = self.locator("textbox", "Email")
        self.password_input = self.locator("textbox", "Password")
