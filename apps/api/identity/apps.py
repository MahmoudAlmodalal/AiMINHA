from django.apps import AppConfig


class IdentityConfig(AppConfig):
    name = "identity"

    def ready(self) -> None:
        from identity import schema  # noqa: F401 -- register the DRF authentication extension.
