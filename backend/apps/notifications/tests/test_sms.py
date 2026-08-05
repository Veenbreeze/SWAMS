from apps.notifications.services.sms import NoOpSmsProvider, sms_provider


def test_noop_sms_provider_never_raises_and_returns_none():
    provider = NoOpSmsProvider()
    assert provider.send(phone_number="+255700000000", message="hi") is None
    assert provider.send(phone_number="", message="hi") is None


def test_module_level_provider_is_a_noop_instance():
    assert isinstance(sms_provider, NoOpSmsProvider)
