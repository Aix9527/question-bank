def test_subjects_are_seeded(client):
    response = client.get('/api/subjects')
    assert response.status_code == 200
    assert [item['code'] for item in response.json()] == ['chinese', 'math', 'english']
    assert [item['name'] for item in response.json()] == ['语文', '数学', '英语']
