"""État applicatif partagé entre les vues (stocké dans page.session)."""


class AppState:
    def __init__(self):
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.temp_token: str | None = None  # en attente de code MFA
        self.user: dict | None = None  # {id, email, username, role, phone}

    @property
    def is_authenticated(self):
        return self.access_token is not None and self.user is not None

    @property
    def role(self):
        return self.user["role"] if self.user else None

    def reset(self):
        self.access_token = None
        self.refresh_token = None
        self.temp_token = None
        self.user = None
