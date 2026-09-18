from playwright.sync_api import Page, Locator

from automation_infra.core.web.pages.base_page import BasePage


class SeatingPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.continue_to_checkout_button = self.locator("button", "Continue to checkout", exact=True)

    def seat_button(self, name: str) -> Locator:
        return self.locator("button", name, exact=True)
