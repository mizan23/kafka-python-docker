"""
Create NSP Subscription

- Requests NSP to create a Kafka subscription
- Returns subscription_id and topic_id
"""

import requests
from configuration import SUBSCRIPTION_URL, VERIFY_SSL


def create_subscription(token_mgr):
    headers = {
        "Authorization": f"Bearer {token_mgr.get_access_token()}",
        "Content-Type": "application/json",
    }

    payload = {
        "categories": [{"name": "NSP-FAULT"}]
    }

    response = requests.post(
        SUBSCRIPTION_URL,
        headers=headers,
        json=payload,
        verify=VERIFY_SSL,
    )

    response.raise_for_status()

    data = response.json()["response"]["data"]

    print("✅ Subscription created")
    print("📡 Topic:", data["topicId"])

    return data["subscriptionId"], data["topicId"]