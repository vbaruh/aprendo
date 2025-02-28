import reflex as rx

config = rx.Config(
    app_name="aprendo",
    db_url="sqlite:///aprendo.db",
    env=rx.Env.DEV,
    telemetry_enabled=False,
)
