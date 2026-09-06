"""Tests unitaires du repli automatique de modèle dans gemini_service.

Les quotas free tier Gemini sont PAR MODÈLE : quand le quota journalier du
modèle principal est épuisé (429), l'appel doit basculer sur le modèle suivant
de GEMINI_FALLBACK_MODELS au lieu de faire échouer l'analyse (502).
"""
import pytest

from app.services import gemini_service as gs


class FakeAPIError(Exception):
    """Imite google.genai.errors.APIError (attribut `code`)."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class FakeModels:
    def __init__(self, behavior) -> None:
        self.behavior = behavior  # callable(model, config) -> réponse ou exception
        self.calls: list[tuple[str, object]] = []

    def generate_content(self, model, contents, config):
        self.calls.append((model, config))
        return self.behavior(model, config)


class FakeClient:
    def __init__(self, behavior) -> None:
        self.models = FakeModels(behavior)


@pytest.fixture(autouse=True)
def reset_gemini_state(monkeypatch):
    """Chaque test repart avec une chaîne de modèles et un état connus."""
    monkeypatch.setattr(gs, "_THINKING_SUPPORTED", True)
    monkeypatch.setattr(gs.settings, "gemini_model", "gemini-primary")
    monkeypatch.setattr(gs.settings, "gemini_fallback_models", "gemini-backup,gemini-last")
    monkeypatch.setattr(gs.settings, "gemini_thinking_budget", 0)


def test_fallback_on_daily_quota(monkeypatch):
    """Quota journalier épuisé sur le modèle principal -> modèle suivant."""

    def behavior(model, config):
        if model == "gemini-primary":
            raise FakeAPIError(429, "429 RESOURCE_EXHAUSTED limit: 20 retry in 21h")
        return f"ok:{model}"

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    response, model = gs._generate_content(lambda use_thinking: None, "contents", label="test")

    assert response == "ok:gemini-backup"
    assert model == "gemini-backup"


def test_all_models_exhausted_raises_last_error(monkeypatch):
    """Tous les modèles en quota épuisé -> la dernière erreur est propagée."""

    def behavior(model, config):
        raise FakeAPIError(429, f"429 RESOURCE_EXHAUSTED on {model} retry in 21h")

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    with pytest.raises(FakeAPIError):
        gs._generate_content(lambda use_thinking: None, "contents", label="test")


def test_thinking_rejected_then_retried_without(monkeypatch):
    """ThinkingConfig rejeté (400) -> réessaie la chaîne sans thinking."""
    seen_configs: list[object] = []

    def behavior(model, config):
        seen_configs.append(config)
        if config is not None:  # premier passage : ThinkingConfig présent
            raise FakeAPIError(400, "Thinking config is not supported by this model")
        return f"ok:{model}"

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    response, model = gs._generate_content(
        lambda use_thinking: {"thinking": True} if use_thinking else None,
        "contents",
        label="test",
    )

    assert response == "ok:gemini-primary"
    assert model == "gemini-primary"
    assert gs._THINKING_SUPPORTED is False
    assert seen_configs[-1] is None


def test_server_error_falls_back_to_next_model(monkeypatch):
    """503 persistant sur le principal (après retries) -> modèle suivant.

    Cas réel du 06/09 : gemini-3.7-flash a renvoyé 503 à deux reprises après
    le repli depuis le modèle principal ; l'analyse échouait au lieu de
    tester gemini-3.8-flash.
    """
    monkeypatch.setattr(gs.time, "sleep", lambda seconds: None)  # accélère les retries

    def behavior(model, config):
        if model in ("gemini-primary", "gemini-backup"):
            raise FakeAPIError(503, f"503 UNAVAILABLE - service overloaded on {model}")
        return f"ok:{model}"

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    response, model = gs._generate_content(lambda use_thinking: None, "contents", label="test")

    assert response == "ok:gemini-last"
    assert model == "gemini-last"


def test_all_models_overloaded_raises_last_error(monkeypatch):
    """Tous les modèles en 503 persistant -> la dernière erreur est propagée."""
    monkeypatch.setattr(gs.time, "sleep", lambda seconds: None)

    def behavior(model, config):
        raise FakeAPIError(503, f"503 UNAVAILABLE on {model}")

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    with pytest.raises(FakeAPIError):
        gs._generate_content(lambda use_thinking: None, "contents", label="test")


def test_unhandled_error_still_raises_immediately(monkeypatch):
    """Une erreur non transitoire (ex. 403 permission) échoue sans repli."""
    calls: list[str] = []

    def behavior(model, config):
        calls.append(model)
        raise FakeAPIError(403, "403 PERMISSION_DENIED - API not enabled")

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    with pytest.raises(FakeAPIError):
        gs._generate_content(lambda use_thinking: None, "contents", label="test")
    assert calls == ["gemini-primary"]  # aucun repli sur les modèles suivants


def test_daily_quota_without_limit_name_detected(monkeypatch):
    """Format sans 'PerDay' mais avec 'retry in Xh' -> détecté comme journalier."""
    exc = FakeAPIError(429, " RESOURCE_EXHAUSTED ... Please retry in 21.5h. ")
    assert gs._is_daily_quota(exc) is True

    per_minute = FakeAPIError(429, " RESOURCE_EXHAUSTED ... Please retry in 22s. ")
    assert gs._is_daily_quota(per_minute) is False


def test_fallback_skips_unavailable_model(monkeypatch):
    """Modèle de secours retiré pour la clé (404) -> passe au modèle suivant."""

    def behavior(model, config):
        if model == "gemini-primary":
            raise FakeAPIError(429, "429 RESOURCE_EXHAUSTED retry in 21h")
        if model == "gemini-backup":
            raise FakeAPIError(404, "This model models/gemini-backup is no longer available to new users.")
        return f"ok:{model}"

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    response, model = gs._generate_content(lambda use_thinking: None, "contents", label="test")

    assert response == "ok:gemini-last"
    assert model == "gemini-last"


def test_chain_exhausted_raises_quota_error(monkeypatch):
    """Chaîne épuisée (quota + 404) -> l'erreur de quota est propagée (message explicite)."""

    def behavior(model, config):
        if model == "gemini-primary":
            raise FakeAPIError(429, "429 RESOURCE_EXHAUSTED retry in 21h")
        raise FakeAPIError(404, "This model is no longer available to new users.")

    monkeypatch.setattr(gs, "_client", lambda: FakeClient(behavior))

    with pytest.raises(FakeAPIError) as info:
        gs._generate_content(lambda use_thinking: None, "contents", label="test")
    assert "429" in str(info.value)
