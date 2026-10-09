"""Plan model for a travel eSIM data offer."""

from dataclasses import asdict, dataclass

FIELDS = ("provider", "country", "data_gb", "validity_days", "price_usd", "notes")


@dataclass
class Plan:
    """A single eSIM data plan offered by a provider for a country."""

    provider: str
    country: str
    data_gb: float
    validity_days: int
    price_usd: float
    notes: str = ""

    def __post_init__(self):
        for name in ("provider", "country"):
            if not str(getattr(self, name) or "").strip():
                raise ValueError(f"{name} must not be empty")
        self.data_gb = float(self.data_gb)
        self.validity_days = int(self.validity_days)
        self.price_usd = float(self.price_usd)
        if self.data_gb <= 0:
            raise ValueError("data_gb must be positive")
        if self.validity_days <= 0:
            raise ValueError("validity_days must be positive")
        if self.price_usd < 0:
            raise ValueError("price_usd must not be negative")

    @property
    def price_per_gb(self) -> float:
        """Price in USD per gigabyte of data."""
        return self.price_usd / self.data_gb

    @classmethod
    def from_row(cls, row):
        """Build a Plan from a CSV row (dict of strings)."""
        return cls(
            provider=row["provider"],
            country=row["country"],
            data_gb=row["data_gb"],
            validity_days=row["validity_days"],
            price_usd=row["price_usd"],
            notes=row.get("notes") or "",
        )

    def to_row(self):
        """Serialize to a CSV row (dict of strings)."""
        d = asdict(self)
        d["data_gb"] = f"{self.data_gb:g}"
        d["price_usd"] = f"{self.price_usd:g}"
        return d
