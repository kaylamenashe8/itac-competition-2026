from playwright.sync_api import Page, Locator


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def locator(self, role: str, name: str, **kwargs) -> Locator:
        return self.page.get_by_role(role, name=name, **kwargs)

    def locator_by_css(self, selector: str) -> Locator:
        return self.page.locator(selector)
