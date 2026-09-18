from playwright.sync_api import Page

from automation_infra.core.web.pages.event_pages.events_page import EventsPage
from automation_infra.core.web.pages.event_pages.seating_page import SeatingPage


class PurchaseFlows:
    def __init__(self, page: Page):
        self.page = page
        self.events_page = EventsPage(page)
        self.seating_page = SeatingPage(page)

    def open_event(self, event_id: str):
        self.page.goto("/events")
        self.events_page.view_event(event_id).click()

    def select_seat(self, seat_name: str, force: bool = False):
        self.seating_page.seat_button(seat_name).click(force=force)

    def continue_to_checkout(self):
        self.seating_page.continue_to_checkout_button.click()
