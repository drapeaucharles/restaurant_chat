import requests
import uuid

url = "https://restaurantchat-production.up.railway.app/chat"
client_id = str(uuid.uuid4())

# Test 3 different questions
questions = [
    "What pasta dishes do you have?",
    "Can I bring my pet dragon?",
    "¿Qué postres tienen?"
]

for q in questions:
    print(f"\nQ: {q}")
    r = requests.post(url, json={
        "restaurant_id": "bella_vista_restaurant",
        "client_id": client_id,
        "sender_type": "client",
        "message": q
    })
    if r.status_code == 200:
        answer = r.json()['answer']
        print(f"A: {answer[:150]}...")
        print(f"Length: {len(answer)} chars")
