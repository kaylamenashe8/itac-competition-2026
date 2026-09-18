from playwright.sync_api import Page

from automation_infra.core.web.pages.base_page import BasePage


class CheckoutPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.checkout_header = self.locator("heading", "Checkout", exact=True, level=1)
