from playwright.sync_api import Page

from automation_infra.core.web.pages.authentication_pages.base_auth_page import BaseAuthPage


class LoginPage(BaseAuthPage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.login_header = self.locator("heading", "Log in to Arena")
        self.login_button = self.locator("button", "Log in")
        self.create_account_link = self.locator("link", "Sign up with your email")
