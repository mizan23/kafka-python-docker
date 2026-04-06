"""
Kafka Consumer (Main Processing Loop)

Flow per message:
1. Poll Kafka
2. Decode JSON
3. Normalize alarm
4. Apply lifecycle (DB + cache)
5. Commit offset
"""

import json
import traceback
from confluent_kafka import Consumer

from configuration import NSP_SERVER, KAFKA_KEYSTORE_PASSWORD
from alarm_normalizer import normalize_alarm
from alarm_lifecycle import handle_alarm_lifecycle


def start_kafka_consumer(topic, stop_event, alarm_cache):

    # ============================================================
    # KAFKA CONFIG
    # ============================================================
    conf = {
        "bootstrap.servers": f"{NSP_SERVER}:9193",
        "group.id": "nsp-alarm-consumer",

        # Manual offset control (important)
        "enable.auto.commit": False,
        "auto.offset.reset": "latest",

        # SSL
        "security.protocol": "SSL",
        "ssl.keystore.location": "nsp_keystore.p12",
        "ssl.keystore.password": KAFKA_KEYSTORE_PASSWORD,
        "ssl.ca.location": "ca.pem",
    }

    consumer = Consumer(conf)
    consumer.subscribe([topic])

    print("📡 Kafka consumer started")
    print(f"📥 Listening on topic: {topic}")

    # ============================================================
    # MAIN LOOP
    # ============================================================
    try:
        while not stop_event.is_set():

            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                print("❌ Kafka error:", msg.error())
                continue

            # ----------------------------------------------------
            # 1. DECODE MESSAGE
            # ----------------------------------------------------
            try:
                event = json.loads(msg.value().decode())
            except Exception as e:
                print("❌ Invalid JSON:", e)
                continue

            # ----------------------------------------------------
            # 2. NORMALIZE ALARM
            # ----------------------------------------------------
            try:
                alarm = normalize_alarm(event, alarm_cache)
            except Exception:
                print("❌ normalize_alarm() failed")
                traceback.print_exc()
                continue

            # Dropped by filter
            if not alarm:
                continue

            # ----------------------------------------------------
            # 3. HANDLE LIFECYCLE (DB + CACHE)
            # ----------------------------------------------------
            try:
                handle_alarm_lifecycle(alarm, alarm_cache)

                # Commit only AFTER success
                consumer.commit(msg, asynchronous=False)

            except Exception:
                print("❌ handle_alarm_lifecycle() failed")
                traceback.print_exc()
                continue

            # ----------------------------------------------------
            # 4. LOG OUTPUT
            # ----------------------------------------------------
            print("\n🚨 ALARM")
            print(json.dumps(alarm, indent=2, default=str))

    finally:
        consumer.close()
        print("🛑 Kafka consumer stopped")