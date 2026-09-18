# asserts that we are on a specific screen

from playwright.sync_api import Page, expect

from automation_infra.core.web.pages.authentication_pages.login_page import LoginPage
from automation_infra.core.web.pages.authentication_pages.registration_page import RegistrationPage
from automation_infra.core.web.pages.event_pages.events_page import EventsPage
from automation_infra.core.web.pages.purchase_pages.checkout_page import CheckoutPage



class AssertOnScreen:
    def __init__(self, page: Page):
        self.page = page
        self.login_page = LoginPage(page)
        self.registration_page = RegistrationPage(page)
        self.events_page = EventsPage(page)
        self.checkout_page = CheckoutPage(page)

    def verify_login_screen(self):
        expect(self.login_page.login_header).to_be_visible()

    def verify_registration_screen(self):
        expect(self.registration_page.registration_header).to_be_visible()

    def verify_events_main_screen(self):
        expect(self.events_page.events_header).to_be_visible()

    def verify_checkout_screen(self):
        expect(self.checkout_page.checkout_header).to_be_visible()

    def verify_checkout_screen_not_shown(self):
        expect(self.checkout_page.checkout_header).not_to_be_visible()