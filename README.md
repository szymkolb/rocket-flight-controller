# Rocket Flight Controller

Program w Pythonie automatyzujący procedurę tankowania, startu, lotu i lądowania rakiety w symulatorze AGH Space Systems.

## Funkcjonalność

- Automatyczne tankowanie paliwa i utleniacza.
- Kontrola ciśnienia utleniacza.
- Sterowanie zaworami, grzałką i zapłonem.
- Wykrywanie apogeum i uruchamianie spadochronu.
- Monitorowanie parametrów lotu i wykrywanie lądowania.

Program steruje rakietą na podstawie danych z sensorów, przechodząc między kolejnymi fazami lotu.

## Uruchomienie

Wymagany jest Python oraz biblioteki `crccheck`, `bitstruct` i `pyyaml`.

Instalacja zależności:

```bash
pip install crccheck bitstruct pyyaml
```

Uruchomienie w osobnych terminalach, w podanej kolejności:

```bash
python tcp_proxy.py
python tcp_simulator.py
python main.py
```

Program łączy się z proxy przez TCP na adresie `127.0.0.1:3000`.

## Struktura projektu

- `main.py` – implementacja sterownika lotu.
- `communication_library/` – biblioteka komunikacyjna dostarczona w zadaniu.
- `tcp_proxy.py` – proxy komunikacyjne dostarczone w zadaniu.
- `tcp_simulator.py` – symulator rakiety dostarczony w zadaniu.
- `simulator_config.yaml` – konfiguracja symulatora.

## Autorstwo

`main.py` został napisany w ramach zadania rekrutacyjnego do sekcji Rocket Software koła naukowego AGH Space Systems. Pozostałe wymienione komponenty zostały udostępnione przez organizatorów zadania.