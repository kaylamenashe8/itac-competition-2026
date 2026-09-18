from playwright.sync_api import Page, Locator

from automation_infra.core.web.pages.base_page import BasePage


class EventsPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.events_header = self.locator("heading", "Events", exact=True, level=1)

    def view_event(self, event_id: str) -> Locator:
        return self.locator_by_css(f'a[href="/events/{event_id}"]')
