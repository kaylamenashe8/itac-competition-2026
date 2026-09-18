from playwright.sync_api import Page

from automation_infra.core.web.pages.authentication_pages.base_auth_page import BaseAuthPage


class RegistrationPage(BaseAuthPage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.registration_header = self.locator("heading", "Create your account")
        self.create_workspace_button = self.locator("button", "Create workspace")
        self.login_link = self.locator("link", "Log in")