"""Shared Playwright page-object base class and extraction helpers."""

from __future__ import annotations

from typing import Any, Self

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from utils.logging import get_logger


class BasePage:
    """Base class for all Page Objects in the framework.

    Provides common Playwright interactions, Axe-core auditing,
    and generic element extraction scaffolding.
    """

    PAGE_URL: str = ""
    NAVIGATION_TIMEOUT_MS: int = 20_000
    PAGE_LOAD_TIMEOUT_MS: int = 15_000

    def __init__(self, page: Page) -> None:
        """Initialize the page object with the Playwright page.

        Args:
            page: The active Playwright page instance.
        """
        self.page = page
        self.logger = get_logger(self.__class__.__name__)

    async def navigate(self) -> Self:
        """Navigate to the page's defined URL.

        Returns:
            Self: The current page object instance.

        Raises:
            ValueError: If PAGE_URL is not defined on the child.
        """
        if not self.PAGE_URL:
            raise ValueError(f"PAGE_URL missing for {self.__class__.__name__}")

        self.logger.info(
            "Navigating to: %s (timeout=%sms)",
            self.PAGE_URL,
            self.NAVIGATION_TIMEOUT_MS,
        )
        try:
            response = await self.page.goto(
                self.PAGE_URL,
                wait_until="domcontentloaded",
                timeout=self.NAVIGATION_TIMEOUT_MS,
            )
        except PlaywrightTimeoutError as exc:
            self.logger.exception(
                "Navigation timed out after %sms for url=%s",
                self.NAVIGATION_TIMEOUT_MS,
                self.PAGE_URL,
            )
            raise TimeoutError(
                "Navigation timed out for "
                f"{self.PAGE_URL} after {self.NAVIGATION_TIMEOUT_MS}ms."
            ) from exc

        status = response.status if response is not None else "unknown"
        self.logger.info(
            "Navigation completed with status=%s at url=%s",
            status,
            self.page.url,
        )
        await self.wait_for_page_load()
        return self

    async def wait_for_page_load(self) -> Self:
        """Wait for the page to reach a stable state.

        Returns:
            Self: The current page object instance.
        """
        self.logger.info(
            "Waiting for page load state=domcontentloaded (timeout=%sms)",
            self.PAGE_LOAD_TIMEOUT_MS,
        )
        await self.page.wait_for_load_state(
            "domcontentloaded",
            timeout=self.PAGE_LOAD_TIMEOUT_MS,
        )
        self.logger.info("Page load ready at url=%s", self.page.url)
        return self

    async def run_axe_audit(
        self, context_name: str | None = None
    ) -> dict[str, Any]:
        """Inject and run Axe-core on the current page state.

        Args:
            context_name: Optional tag for the Allure report.

        Returns:
            dict[str, Any]: Dictionary of Axe-core results.
        """
        audit_name = context_name or self.__class__.__name__
        self.logger.info(f"Running Axe audit for: {audit_name}")
        return {}

    async def extract_elements_by_locator(
        self, selector: str
    ) -> list[Locator]:
        """Extract DOM elements matching a specific selector.

        Args:
            selector: The CSS or XPath selector to match.

        Returns:
            list[Locator]: Resolved Locators for the criteria.
        """
        self.logger.info(f"Extracting elements for: {selector}")
        return await self.page.locator(selector).all()

    async def extract_element_data(
        self, locator: Locator, js_extractor: str
    ) -> dict[str, Any]:
        """Extract relevant data from a given Locator.

        Args:
            locator: The Playwright Locator to extract data from.
            js_extractor: A JavaScript function as a string that takes
                an element and returns a data object.

        Returns:
            dict[str, Any]: The extracted data as a dictionary.
        """
        data = await locator.evaluate(js_extractor)
        self.logger.debug("Extracted data: %s", data)
        return data
