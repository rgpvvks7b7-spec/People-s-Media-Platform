from .base import BaseAdsProvider


class MetaAdsProvider(BaseAdsProvider):
    network_id = "meta"

    def validate_campaign(self, campaign):
        errors = []
        if "meta" not in (campaign.ad_networks or []):
            return errors
        if not campaign.destination_url:
            errors.append("Destination URL is required for Meta ads.")
        return errors

    def launch(self, campaign):
        return {
            "integration": "coming_soon",
            "network": self.network_id,
            "remote_id": "",
            "status": "not_connected",
        }

    def pause(self, campaign):
        return {
            "integration": "coming_soon",
            "network": self.network_id,
            "status": "not_connected",
        }

    def get_remote_status(self, campaign):
        return {
            "integration": "coming_soon",
            "network": self.network_id,
            "remote_id": "",
            "status": "not_connected",
        }


class GoogleAdsProvider(BaseAdsProvider):
    network_id = "google"

    def validate_campaign(self, campaign):
        return []

    def launch(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}

    def pause(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "status": "not_connected"}

    def get_remote_status(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}


class TikTokAdsProvider(BaseAdsProvider):
    network_id = "tiktok"

    def validate_campaign(self, campaign):
        return []

    def launch(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}

    def pause(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "status": "not_connected"}

    def get_remote_status(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}


class SpotifyAdsProvider(BaseAdsProvider):
    network_id = "spotify"

    def validate_campaign(self, campaign):
        return []

    def launch(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}

    def pause(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "status": "not_connected"}

    def get_remote_status(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}


class YouTubeAdsProvider(BaseAdsProvider):
    network_id = "youtube"

    def validate_campaign(self, campaign):
        return []

    def launch(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}

    def pause(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "status": "not_connected"}

    def get_remote_status(self, campaign):
        return {"integration": "coming_soon", "network": self.network_id, "remote_id": "", "status": "not_connected"}


PROVIDER_REGISTRY = {
    "meta": MetaAdsProvider,
    "google": GoogleAdsProvider,
    "tiktok": TikTokAdsProvider,
    "spotify": SpotifyAdsProvider,
    "youtube": YouTubeAdsProvider,
}


def get_provider(network_id):
    provider_cls = PROVIDER_REGISTRY.get(network_id)
    if not provider_cls:
        return None
    return provider_cls()


def validate_campaign_for_networks(campaign):
    errors = []
    for network_id in campaign.ad_networks or []:
        provider = get_provider(network_id)
        if provider:
            errors.extend(provider.validate_campaign(campaign))
    return errors
