from city_explorer.city_resolver import CityResolver


def test_historical_city_name_gets_modern_suggestion() -> None:
    resolver = CityResolver()
    result = resolver.resolve("Leningrad")

    assert result.ok
    assert result.data is not None
    assert "saint petersburg" in result.data.canonical_name.lower()
    assert "устарело" in result.data.warning.lower()


def test_known_preset_city_without_network() -> None:
    resolver = CityResolver()
    result = resolver.resolve("Moscow")

    assert result.ok
    assert result.data is not None
    assert result.data.country
    assert result.data.max_lat > result.data.min_lat
