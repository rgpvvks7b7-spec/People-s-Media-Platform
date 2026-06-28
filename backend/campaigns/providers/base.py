from abc import ABC, abstractmethod


class BaseAdsProvider(ABC):
    network_id: str = ""

    @abstractmethod
    def validate_campaign(self, campaign) -> list[str]:
        """Return a list of validation error messages."""

    @abstractmethod
    def launch(self, campaign) -> dict:
        """Launch campaign on the ad network."""

    @abstractmethod
    def pause(self, campaign) -> dict:
        """Pause a running campaign."""

    @abstractmethod
    def get_remote_status(self, campaign) -> dict:
        """Fetch remote campaign status."""
