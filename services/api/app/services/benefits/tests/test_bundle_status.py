from app.conftest import auth


def test_bundle_items_have_plain_status_labels(client):
    b = client.post("/api/benefits/bundles/match", headers=auth("stefan"),
                    json={"text": "Ich möchte etwas für meine Gesundheit tun."}).json()
    by = {i["ref_id"]: i for i in b["items"] if i["kind"] in ("benefit", "offer")}
    assert by["vorsorgeuntersuchung"]["status_de"] == "kostenlos nutzbar"
    assert by["angebot_bewegt_im_park"]["status_de"] == "kostenlos nutzbar"
    prev = [i for i in b["items"] if i["kind"] == "prevention"]
    assert prev and all(i["status_de"] for i in prev)
