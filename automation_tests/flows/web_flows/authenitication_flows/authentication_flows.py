from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from automation_infra.core.web.pages.authentication_pages.login_page import LoginPage
from automation_infra.core.web.pages.authentication_pages.registration_page import RegistrationPage


class AuthenticationFlows:
    def __init__(self, page: Page):
        self.page = page
        self.login_page = LoginPage(page)
        self.registration_page = RegistrationPage(page)

    def login(self, email: str, password: str):
        # fills login creds and taps login button
        self.navigate_to_login_page()
        self.login_page.email_input.fill(email)
        self.login_page.password_input.fill(password)
        self.login_page.login_button.click()

    def navigate_to_login_page(self):
        if self.login_page.login_header.is_visible():
            return
        elif self.registration_page.registration_header.is_visible():
            self.registration_page.login_link.click()
        else:
            raise ValueError("Not currently located in login or registration page")


    def register(self, email: str, password: str):
        self.navigate_to_registration_page()
        self.registration_page.email_input.fill(email)
        self.registration_page.password_input.fill(password)
        self.registration_page.create_workspace_button.click()

    def navigate_to_registration_page(self):
        if self.registration_page.registration_header.is_visible():
            return
        elif self.login_page.login_header.is_visible():
            self.login_page.create_account_link.click()
        else:
            raise ValueError("Not currently located in login or registration page")





