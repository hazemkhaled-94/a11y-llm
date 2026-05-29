"""Page object for the Deque University Mars demo."""

from __future__ import annotations

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from web.base.base_page import BasePage


class MarsDemoPage(BasePage):
    """Page object for the static Mars demo page."""

    PAGE_URL = "https://dequeuniversity.com/demo/mars/"
    READY_SELECTOR = "body"
    READY_TIMEOUT_MS = 10_000

    async def open(self) -> "MarsDemoPage":
        """Open the Mars demo page and wait for visible content."""
        await self.navigate()

        try:
            await self.page.locator(self.READY_SELECTOR).first.wait_for(
                state="visible",
                timeout=self.READY_TIMEOUT_MS,
            )
        except PlaywrightTimeoutError as exc:
            self.logger.exception(
                "Mars demo page did not become ready at url=%s",
                self.page.url,
            )
            raise TimeoutError(
                "Mars demo page did not become ready after "
                f"{self.READY_TIMEOUT_MS}ms."
            ) from exc

        self.logger.info("Mars demo page is ready at url=%s", self.page.url)
        return self
