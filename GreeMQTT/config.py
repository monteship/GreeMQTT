from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from GreeMQTT.logger import log

DEFAULT_PARAMS = (
    "Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,"
    "SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen"
)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Network ---
    network: str = Field(default="", alias="NETWORK")

    # --- MQTT ---
    mqtt_broker: str = Field(alias="MQTT_BROKER")
    mqtt_port: int = Field(default=1883, alias="MQTT_PORT")
    mqtt_user: str | None = Field(default=None, alias="MQTT_USER")
    mqtt_password: str | None = Field(default=None, alias="MQTT_PASSWORD")
    mqtt_topic: str = Field(default="gree", alias="MQTT_TOPIC")
    mqtt_qos: int = Field(default=0, alias="MQTT_QOS")
    mqtt_retain: bool = Field(default=False, alias="MQTT_RETAIN")
    mqtt_keep_alive: int = Field(default=60, alias="MQTT_KEEP_ALIVE")

    # --- Polling ---
    update_interval: int = Field(default=3, alias="UPDATE_INTERVAL")
    adaptive_polling_timeout: int = Field(default=45, alias="ADAPTIVE_POLLING_TIMEOUT")
    adaptive_fast_interval: float = Field(default=0.8, alias="ADAPTIVE_FAST_INTERVAL")

    # --- Event queue ---
    event_queue_workers: int = Field(default=5, alias="EVENT_QUEUE_WORKERS")
    immediate_response_timeout: float = Field(default=5.0, alias="IMMEDIATE_RESPONSE_TIMEOUT")

    # --- Tracking params ---
    tracking_params: str = Field(default="", alias="TRACKING_PARAMS")

    @property
    def network_list(self) -> list[str]:
        if not self.network:
            return []
        return [item.strip() for item in self.network.split(",") if item.strip()]

    @property
    def tracking_params_list(self) -> list[str]:
        if not self.tracking_params:
            return [p.strip() for p in DEFAULT_PARAMS.split(",") if p.strip()]
        return [item.strip() for item in self.tracking_params.split(",") if item.strip()]

    @field_validator("mqtt_qos")
    @classmethod
    def validate_qos(cls, v: int) -> int:
        if v not in (0, 1, 2):
            raise ValueError("MQTT_QOS must be 0, 1, or 2.")
        return v


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    s = AppSettings()
    log.debug(
        "Initialized MQTT with",
        broker=s.mqtt_broker,
        port=s.mqtt_port,
        user=s.mqtt_user,
        password="*" * len(s.mqtt_password) if s.mqtt_password else None,
        topic=s.mqtt_topic,
        qos=s.mqtt_qos,
        retain=s.mqtt_retain,
        keep_alive=s.mqtt_keep_alive,
    )
    log.debug(
        "Initialized GreeMQTT with",
        network=s.network_list,
        update_interval=s.update_interval,
        params=s.tracking_params_list,
    )
    return s


settings = get_settings()
